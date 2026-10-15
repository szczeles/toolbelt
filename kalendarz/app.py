import os
import sqlite3
from flask import Flask, jsonify, request, g, render_template_string

app = Flask(__name__)

# Konfiguracja: Hasło wymagane do zapisywania (dodawanie/edycja/usuwanie biegów)
ADMIN_PASSWORD = os.environ.get("RUN_PASSWORD")
DATABASE = "/data/runs.db"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT,
                location TEXT NOT NULL,
                distance TEXT NOT NULL,
                description TEXT,
                link TEXT,
                contributor TEXT,
                rsvps INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

# --- Endpointy API ---

@app.route('/api/events', methods=['GET'])
def get_events():
    """Publiczny dostęp tylko do odczytu: Pobierz wszystkie biegi."""
    db = get_db()
    cursor = db.execute('SELECT * FROM events ORDER BY date ASC, time ASC')
    events = [dict(row) for row in cursor.fetchall()]
    return jsonify(events)

@app.route('/api/events', methods=['POST'])
def add_event():
    """Dostęp do zapisu: Dodaj nowy bieg (wymaga hasła)."""
    password = request.headers.get('X-Password') or request.json.get('password')
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Brak autoryzacji. Wymagane poprawne hasło do zapisu."}), 401

    data = request.json
    if not data or not data.get('title') or not data.get('date') or not data.get('location'):
        return jsonify({"error": "Brak wymaganych pól (tytuł, data, lokalizacja)."}), 400

    db = get_db()
    cursor = db.execute('''
        INSERT INTO events (title, date, time, location, distance, description, link, contributor, rsvps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (
        data.get('title'),
        data.get('date'),
        data.get('time', ''),
        data.get('location'),
        data.get('distance', '5K'),
        data.get('description', ''),
        data.get('link', ''),
        data.get('contributor', 'Anonim')
    ))
    db.commit()
    
    new_id = cursor.lastrowid
    return jsonify({"success": True, "id": new_id, "message": "Dodano bieg pomyślnie."}), 201

@app.route('/api/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    """Dostęp do zapisu: Edytuj bieg (wymaga hasła)."""
    password = request.headers.get('X-Password') or request.json.get('password')
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Brak autoryzacji. Wymagane poprawne hasło do zapisu."}), 401

    data = request.json
    db = get_db()
    db.execute('''
        UPDATE events 
        SET title = ?, date = ?, time = ?, location = ?, distance = ?, description = ?, link = ?, contributor = ?
        WHERE id = ?
    ''', (
        data.get('title'),
        data.get('date'),
        data.get('time', ''),
        data.get('location'),
        data.get('distance', '5K'),
        data.get('description', ''),
        data.get('link', ''),
        data.get('contributor', 'Anonim'),
        event_id
    ))
    db.commit()
    return jsonify({"success": True, "message": "Zaktualizowano bieg pomyślnie."})

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Dostęp do zapisu: Usuń bieg (wymaga hasła)."""
    password = request.headers.get('X-Password') or request.json.get('password')
    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Brak autoryzacji. Wymagane poprawne hasło do zapisu."}), 401

    db = get_db()
    db.execute('DELETE FROM events WHERE id = ?', (event_id,))
    db.commit()
    return jsonify({"success": True, "message": "Usunięto bieg pomyślnie."})

@app.route('/api/events/<int:event_id>/rsvp', methods=['POST'])
def rsvp_event(event_id):
    """Publiczne zgłoszenie udziału."""
    db = get_db()
    db.execute('UPDATE events SET rsvps = rsvps + 1 WHERE id = ?', (event_id,))
    db.commit()
    cursor = db.execute('SELECT rsvps FROM events WHERE id = ?', (event_id,))
    row = cursor.fetchone()
    return jsonify({"success": True, "rsvps": row['rsvps'] if row else 0})

@app.route('/api/verify', methods=['POST'])
def verify_password():
    """Weryfikacja hasła dla trybu kontrybutora."""
    data = request.json or {}
    password = data.get('password')
    if password == ADMIN_PASSWORD:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Nieprawidłowe hasło"}), 401


# --- Interfejs użytkownika (UI) ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Park Team Toruń - kalendarz</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col font-sans">

    <!-- Nagłówek -->
    <header class="bg-indigo-600 text-white shadow-md">
        <div class="max-w-6xl mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
            <div class="flex items-center space-x-3">
                <div class="bg-white/10 p-2.5 rounded-xl"><i class="fa-solid fa-person-running text-2xl"></i></div>
                <div>
                    <h1 class="text-xl font-bold tracking-tight">Park Team Toruń - kalendarz</h1>
                    <p class="text-xs text-indigo-200">Kiedy i gdzie biegamy</p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <div id="contributorStatus" class="hidden text-xs bg-emerald-500/20 text-emerald-100 border border-emerald-400/30 px-3 py-1.5 rounded-full font-medium flex items-center gap-1.5">
                    <i class="fa-solid fa-shield-halved"></i> Tryb Kontrybutora Aktywny
                </div>
                <button id="authBtn" onclick="openAuthModal()" class="bg-white/10 hover:bg-white/20 border border-white/20 px-4 py-2 rounded-xl text-sm font-medium transition flex items-center gap-2">
                    <i id="authIcon" class="fa-solid fa-lock"></i> <span id="authBtnText">Logowanie</span>
                </button>
                <button id="addEventBtn" onclick="openEventModal()" class="hidden bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow transition flex items-center gap-2">
                    <i class="fa-solid fa-plus"></i> Dodaj Bieg
                </button>
            </div>
        </div>
    </header>

    <!-- Główna zawartość -->
    <main class="max-w-6xl mx-auto px-4 py-8 flex-grow w-full">
        <!-- Sterowanie i filtry -->
        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 mb-6 flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="flex items-center space-x-2 w-full md:w-auto">
                <button onclick="changeMonth(-1)" class="p-2 hover:bg-slate-100 rounded-lg text-slate-600 transition"><i class="fa-solid fa-chevron-left"></i></button>
                <h2 id="currentMonthYear" class="text-lg font-bold min-w-[180px] text-center"></h2>
                <button onclick="changeMonth(1)" class="p-2 hover:bg-slate-100 rounded-lg text-slate-600 transition"><i class="fa-solid fa-chevron-right"></i></button>
                <button onclick="goToToday()" class="text-xs bg-slate-100 hover:bg-slate-200 font-medium px-3 py-1.5 rounded-lg text-slate-600 transition">Dzisiaj</button>
            </div>
            <div class="flex flex-wrap items-center gap-3 w-full md:w-auto justify-end">
                <div class="relative flex-grow sm:flex-grow-0">
                    <i class="fa-solid fa-search absolute left-3 top-3 text-slate-400 text-sm"></i>
                    <input type="text" id="searchInput" oninput="renderApp()" placeholder="Szukaj biegów..." class="pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500 w-full sm:w-60">
                </div>
                <select id="categoryFilter" onchange="renderApp()" class="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500">
                    <option value="">Wszystkie dystanse</option>
                    <option value="5K">5K</option>
                    <option value="10K">10K</option>
                    <option value="Półmaraton">Półmaraton</option>
                    <option value="Maraton">Maraton</option>
                    <option value="Trail">Trail</option>
                    <option value="Wybieganie">Wybieganie</option>
                    <option value="Inny">Inny</option>
                </select>
            </div>
        </div>

        <!-- Siatka kalendarza i nadchodzące -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Widok kalendarza (2 kolumny) -->
            <div class="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
                <div class="grid grid-cols-7 text-center font-semibold text-xs text-slate-400 mb-4">
                    <div>Pon</div><div>Wt</div><div>Śr</div><div>Czw</div><div>Pt</div><div>Sob</div><div>Nd</div>
                </div>
                <div id="calendarGrid" class="grid grid-cols-7 gap-2"></div>
            </div>

            <!-- Lista nadchodzących biegów (1 kolumna) -->
            <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col h-[600px]">
                <h3 class="font-bold text-slate-800 mb-4 flex items-center justify-between">
                    <span>Nadchodzące biegi</span>
                    <span id="eventCountBadge" class="text-xs bg-indigo-50 text-indigo-600 px-2.5 py-1 rounded-full font-semibold">0 biegów</span>
                </h3>
                <div id="upcomingList" class="overflow-y-auto space-y-3 flex-grow pr-1"></div>
            </div>
        </div>
    </main>

    <!-- Stopka -->
    <footer class="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        Kalendarz biegów drużyny parkrun Toruń
    </footer>

    <!-- Okno logowania -->
    <div id="authModal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm hidden flex items-center justify-center p-4 z-50">
        <div class="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl border border-slate-100">
            <h3 class="font-bold text-lg mb-2">Logowanie Kontrybutora</h3>
            <p class="text-xs text-slate-500 mb-4">Wpisz hasło zespołu, aby włączyć dodawanie i zarządzanie biegami.</p>
            <input type="password" id="passwordInput" placeholder="Hasło" class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm mb-4 focus:outline-none focus:border-indigo-500">
            <div class="flex justify-end space-x-2">
                <button onclick="closeAuthModal()" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-xl transition">Anuluj</button>
                <button onclick="submitPassword()" class="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl shadow transition">Odblokuj</button>
            </div>
        </div>
    </div>

    <!-- Okno dodawania/edycji biegu -->
    <div id="eventModal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm hidden flex items-center justify-center p-4 z-50">
        <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-100 max-h-[90vh] overflow-y-auto">
            <h3 id="modalTitle" class="font-bold text-lg mb-4">Dodaj Nowy Bieg</h3>
            <form id="eventForm" onsubmit="saveEvent(event)" class="space-y-4">
                <input type="hidden" id="eventId">
                <div>
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Tytuł biegu *</label>
                    <input type="text" id="eventTitle" required placeholder="np. Sobotnie długie wybieganie" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Data *</label>
                        <input type="date" id="eventDate" required class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Godzina</label>
                        <input type="time" id="eventTime" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Dystans / Kategoria *</label>
                        <select id="eventDistance" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500">
                            <option value="5K">5K</option>
                            <option value="10K">10K</option>
                            <option value="Półmaraton">Półmaraton</option>
                            <option value="Maraton">Maraton</option>
                            <option value="Trail">Trail</option>
                            <option value="Wybieganie">Wybieganie</option>
                            <option value="Inny">Inny</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 mb-1">Kto dodaje (imię)</label>
                        <input type="text" id="eventContributor" placeholder="np. Izydor" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500">
                    </div>
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Lokalizacja *</label>
                    <input type="text" id="eventLocation" required placeholder="np. Toruń" class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Opis / Notatki</label>
                    <textarea id="eventDescription" rows="3" placeholder="Docelowe tempo, szczegóły spotkania..." class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500"></textarea>
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-600 mb-1">Link do rejestracji lub informacji</label>
                    <input type="url" id="eventLink" placeholder="https://..." class="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500">
                </div>
                <div class="flex justify-end space-x-2 pt-2">
                    <button type="button" onclick="closeEventModal()" class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-xl transition">Anuluj</button>
                    <button type="submit" class="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl shadow transition">Zapisz Bieg</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Logika aplikacji w JavaScript -->
    <script>
        let events = [];
        let currentDate = new Date();
        let isContributor = false;
        let password = localStorage.getItem('run_app_pwd') || '';
        
        fetchEvents();

        if (password) {
            verifyPasswordSilent(password);
        } else {
            renderApp();
        }

        async function verifyPasswordSilent(pwd) {
            try {
                const res = await fetch('/api/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: pwd })
                });
                if (res.ok) {
                    isContributor = true;
                    password = pwd;
                    updateAuthUI();
                } else {
                    localStorage.removeItem('run_app_pwd');
                    password = '';
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function fetchEvents() {
            try {
                const res = await fetch('/api/events');
                events = await res.json();
                renderApp();
            } catch (e) {
                console.error("Nie udało się pobrać biegów:", e);
            }
        }

        function renderApp() {
            renderCalendar();
            renderUpcomingList();
        }

        function changeMonth(dir) {
            currentDate.setMonth(currentDate.getMonth() + dir);
            renderApp();
        }

        function goToToday() {
            currentDate = new Date();
            renderApp();
        }

        function renderCalendar() {
            const grid = document.getElementById('calendarGrid');
            grid.innerHTML = '';

            const year = currentDate.getFullYear();
            const month = currentDate.getMonth();

            const monthNames = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"];
            document.getElementById('currentMonthYear').innerText = `${monthNames[month]} ${year}`;

            const firstDayIndex = (new Date(year, month, 1).getDay() + 6) % 7; // Start od poniedziałku
            const daysInMonth = new Date(year, month + 1, 0).getDate();

            for (let i = 0; i < firstDayIndex; i++) {
                const emptyCell = document.createElement('div');
                emptyCell.className = "h-24 bg-slate-50/50 rounded-xl border border-slate-100 opacity-40";
                grid.appendChild(emptyCell);
            }

            const todayStr = new Date().toISOString().split('T')[0];

            for (let day = 1; day <= daysInMonth; day++) {
                const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const cell = document.createElement('div');
                const isToday = dateStr === todayStr;

                cell.className = `h-24 p-1.5 rounded-xl border flex flex-col justify-between overflow-hidden transition ${isToday ? 'border-indigo-500 bg-indigo-50/20' : 'border-slate-200 bg-white hover:border-slate-300'}`;
                
                if (isContributor) {
                    cell.style.cursor = 'pointer';
                    cell.onclick = (e) => {
                        if (e.target === cell || e.target.tagName === 'SPAN' && !e.target.closest('.event-pill')) {
                            openEventModalForDate(dateStr);
                        }
                    };
                }

                const dayHeader = document.createElement('div');
                dayHeader.className = "flex justify-between items-center text-xs";
                dayHeader.innerHTML = `<span class="font-bold ${isToday ? 'bg-indigo-600 text-white px-1.5 py-0.5 rounded-md' : 'text-slate-700'}">${day}</span>`;
                cell.appendChild(dayHeader);

                const dayEventsContainer = document.createElement('div');
                dayEventsContainer.className = "space-y-1 overflow-y-auto flex-grow pr-0.5";

                const searchQ = document.getElementById('searchInput').value.toLowerCase();
                const catFilter = document.getElementById('categoryFilter').value;

                const dayEvents = events.filter(ev => {
                    if (ev.date !== dateStr) return false;
                    if (catFilter && ev.distance !== catFilter) return false;
                    if (searchQ && !ev.title.toLowerCase().includes(searchQ) && !ev.location.toLowerCase().includes(searchQ)) return false;
                    return true;
                });

                dayEvents.forEach(ev => {
                    const pill = document.createElement('div');
                    pill.className = "event-pill text-[10px] bg-indigo-100 hover:bg-indigo-200 text-indigo-800 font-semibold px-1.5 py-0.5 rounded truncate cursor-pointer flex items-center justify-between";
                    pill.innerHTML = `<span>${ev.title}</span><span class="text-[9px] opacity-75">${ev.distance}</span>`;
                    pill.onclick = (e) => {
                        e.stopPropagation();
                        openEditModal(ev);
                    };
                    dayEventsContainer.appendChild(pill);
                });

                cell.appendChild(dayEventsContainer);
                grid.appendChild(cell);
            }
        }

        function renderUpcomingList() {
            const list = document.getElementById('upcomingList');
            list.innerHTML = '';

            const searchQ = document.getElementById('searchInput').value.toLowerCase();
            const catFilter = document.getElementById('categoryFilter').value;
            const todayStr = new Date().toISOString().split('T')[0];

            const filtered = events.filter(ev => {
                if (ev.date < todayStr) return false;
                if (catFilter && ev.distance !== catFilter) return false;
                if (searchQ && !ev.title.toLowerCase().includes(searchQ) && !ev.location.toLowerCase().includes(searchQ) && !ev.contributor.toLowerCase().includes(searchQ)) return false;
                return true;
            });

            document.getElementById('eventCountBadge').innerText = `${filtered.length} biegów`;

            if (filtered.length === 0) {
                list.innerHTML = `<div class="text-center py-12 text-slate-400 text-sm">Brak nadchodzących biegów.</div>`;
                return;
            }

            filtered.forEach(ev => {
                const item = document.createElement('div');
                item.className = "p-3 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition flex flex-col gap-2";
                
                const badgeColor = getBadgeColor(ev.distance);

                item.innerHTML = `
                    <div class="flex justify-between items-start">
                        <div>
                            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${badgeColor}">${ev.distance}</span>
                            <h4 class="font-bold text-sm text-slate-800 mt-1">${ev.title}</h4>
                        </div>
                        <div class="text-right text-xs text-slate-500 font-medium">
                            <div>${formatDateReadable(ev.date)}</div>
                            ${ev.time ? `<div>${ev.time}</div>` : ''}
                        </div>
                    </div>
                    <div class="text-xs text-slate-600 flex items-center gap-1.5">
                        <i class="fa-solid fa-location-dot text-slate-400"></i> ${ev.location}
                    </div>
                    ${ev.description ? `<p class="text-xs text-slate-500 bg-white p-2 rounded-lg border border-slate-100">${ev.description}</p>` : ''}
                    <div class="flex justify-between items-center pt-1 text-xs">
                        <span class="text-slate-400">Dodane przez <strong class="text-slate-600">${ev.contributor || 'Anonim'}</strong></span>
                        <div class="flex items-center space-x-2">
                            <button onclick="rsvpEvent(${ev.id})" class="bg-indigo-50 hover:bg-indigo-100 text-indigo-600 font-semibold px-2.5 py-1 rounded-lg transition flex items-center gap-1">
                                <i class="fa-solid fa-heart text-xs"></i> <span>${ev.rsvps} idzie</span>
                            </button>
                            ${isContributor ? `
                                <button onclick='openEditModal(${JSON.stringify(ev)})' class="text-slate-400 hover:text-indigo-600 p-1"><i class="fa-solid fa-pen"></i></button>
                                <button onclick="deleteEvent(${ev.id})" class="text-slate-400 hover:text-rose-600 p-1"><i class="fa-solid fa-trash"></i></button>
                            ` : ''}
                        </div>
                    </div>
                `;
                list.appendChild(item);
            });
        }

        function getBadgeColor(distance) {
            switch(distance) {
                case '5K': return 'bg-blue-100 text-blue-700';
                case '10K': return 'bg-emerald-100 text-emerald-700';
                case 'Półmaraton': return 'bg-amber-100 text-amber-700';
                case 'Maraton': return 'bg-purple-100 text-purple-700';
                case 'Trail': return 'bg-stone-200 text-stone-700';
                case 'Wybieganie': return 'bg-indigo-100 text-indigo-700';
                case 'Inny': return 'bg-rose-100 text-rose-700';
                default: return 'bg-slate-100 text-slate-700';
            }
        }

        function formatDateReadable(dateStr) {
            const options = { month: 'short', day: 'numeric' };
            return new Date(dateStr).toLocaleDateString('pl-PL', options);
        }

        function openAuthModal() {
            if (isContributor) {
                if (confirm("Wylogować się z trybu kontrybutora?")) {
                    isContributor = false;
                    password = '';
                    localStorage.removeItem('run_app_pwd');
                    updateAuthUI();
                    renderApp();
                }
            } else {
                document.getElementById('authModal').classList.remove('hidden');
                document.getElementById('passwordInput').value = '';
                document.getElementById('passwordInput').focus();
            }
        }

        function closeAuthModal() {
            document.getElementById('authModal').classList.add('hidden');
        }

        async function submitPassword() {
            const pwd = document.getElementById('passwordInput').value;
            try {
                const res = await fetch('/api/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: pwd })
                });
                if (res.ok) {
                    isContributor = true;
                    password = pwd;
                    localStorage.setItem('run_app_pwd', pwd);
                    closeAuthModal();
                    updateAuthUI();
                    renderApp();
                } else {
                    alert("Nieprawidłowe hasło!");
                }
            } catch (e) {
                alert("Błąd weryfikacji.");
            }
        }

        function updateAuthUI() {
            if (isContributor) {
                document.getElementById('authIcon').className = "fa-solid fa-lock-open";
                document.getElementById('authBtnText').innerText = "Wyloguj";
                document.getElementById('contributorStatus').classList.remove('hidden');
                document.getElementById('addEventBtn').classList.remove('hidden');
            } else {
                document.getElementById('authIcon').className = "fa-solid fa-lock";
                document.getElementById('authBtnText').innerText = "Logowanie";
                document.getElementById('contributorStatus').classList.add('hidden');
                document.getElementById('addEventBtn').classList.add('hidden');
            }
        }

        function openEventModal() {
            document.getElementById('modalTitle').innerText = "Dodaj Nowy Bieg";
            document.getElementById('eventForm').reset();
            document.getElementById('eventId').value = "";
            document.getElementById('eventDate').value = new Date().toISOString().split('T')[0];
            document.getElementById('eventModal').classList.remove('hidden');
        }

        function openEventModalForDate(dateStr) {
            openEventModal();
            document.getElementById('eventDate').value = dateStr;
        }

        function openEditModal(ev) {
            document.getElementById('modalTitle').innerText = "Edytuj Bieg";
            document.getElementById('eventId').value = ev.id;
            document.getElementById('eventTitle').value = ev.title;
            document.getElementById('eventDate').value = ev.date;
            document.getElementById('eventTime').value = ev.time || '';
            document.getElementById('eventDistance').value = ev.distance;
            document.getElementById('eventContributor').value = ev.contributor || '';
            document.getElementById('eventLocation').value = ev.location;
            document.getElementById('eventDescription').value = ev.description || '';
            document.getElementById('eventLink').value = ev.link || '';
            document.getElementById('eventModal').classList.remove('hidden');
        }

        function closeEventModal() {
            document.getElementById('eventModal').classList.add('hidden');
        }

        async function saveEvent(e) {
            e.preventDefault();
            const id = document.getElementById('eventId').value;
            const data = {
                title: document.getElementById('eventTitle').value,
                date: document.getElementById('eventDate').value,
                time: document.getElementById('eventTime').value,
                distance: document.getElementById('eventDistance').value,
                contributor: document.getElementById('eventContributor').value || 'Anonim',
                location: document.getElementById('eventLocation').value,
                description: document.getElementById('eventDescription').value,
                link: document.getElementById('eventLink').value,
                password: password
            };

            const url = id ? `/api/events/${id}` : '/api/events';
            const method = id ? 'PUT' : 'POST';

            try {
                const res = await fetch(url, {
                    method: method,
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Password': password
                    },
                    body: JSON.stringify(data)
                });
                
                if (res.ok) {
                    closeEventModal();
                    fetchEvents();
                } else {
                    const err = await res.json();
                    alert(err.error || "Nie udało się zapisać biegu.");
                }
            } catch (err) {
                alert("Błąd sieci podczas zapisu biegu.");
            }
        }

        async function deleteEvent(id) {
            if (!confirm("Czy na pewno chcesz usunąć ten bieg?")) return;
            try {
                const res = await fetch(`/api/events/${id}`, {
                    method: 'DELETE',
                    headers: { 'X-Password': password },
                    body: JSON.stringify({ password: password })
                });
                if (res.ok) {
                    fetchEvents();
                } else {
                    const err = await res.json();
                    alert(err.error || "Nie udało się usunąć biegu.");
                }
            } catch (err) {
                alert("Błąd sieci.");
            }
        }

        async function rsvpEvent(id) {
            try {
                const res = await fetch(`/api/events/${id}/rsvp`, { method: 'POST' });
                if (res.ok) {
                    fetchEvents();
                }
            } catch (err) {
                console.error(err);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    init_db()
    print("Hasło kontrybutora: " + ADMIN_PASSWORD)
    app.run(debug=True, port=5000, host='0.0.0.0')
