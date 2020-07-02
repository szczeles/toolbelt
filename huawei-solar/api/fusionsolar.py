import logging
import re
from dataclasses import dataclass
from datetime import datetime

import backoff
import requests


@dataclass
class Stats:
    ts: datetime
    values: dict

    def get_daily_energy_wh(self):
        return self.values["day_cap"] * 1000

    def get_current_power_w(self):
        return self.values["active_power"] * 1000


@dataclass
class SignalSet:
    signals: list

    def __repr__(self):
        return repr(self.signals)

    def split_by_unit(self):
        by_unit = {}
        for signal in self.signals:
            if signal.unit not in by_unit:
                by_unit[signal.unit] = SignalSet([])
            by_unit[signal.unit].signals.append(signal)
        return by_unit

    def get_codes(self):
        return [signal.id for signal in self.signals]


@dataclass
class Signal:
    id: str
    unit: str

    def __repr__(self):
        return f'{self.id} ({self.unit.split("Unit")[0]})'


class FusionSolarException(Exception):
    pass


class FusionSolar:
    def __init__(self, username, password, timezone):
        self.username = username
        self.password = password
        self.timezone = timezone
        self.session = None
        self.token = None
        self.station = None

    @backoff.on_exception(
        backoff.expo, (requests.exceptions.RequestException, FusionSolarException)
    )
    def call_api(self, endpoint, body={}):
        url = f"https://eu5.fusionsolar.huawei.com/{endpoint}"
        response = requests.post(
            url=url,
            json=body,
            headers={
                "XSRF-TOKEN": self.token,
                "Referer": "https://eu5.fusionsolar.huawei.com/index.jsp",
            },
            cookies={"JSESSIONID": self.session},
        )

        if response.status_code != 200:
            raise FusionSolarException(f"Invalid response code: {response.status_code}")

        try:
            if response.json()["failCode"] == 306:
                self.login()
                return self.call_api(endpoint, body)
            return response.json()
        except:
            raise FusionSolarException(f"Invalid API output: {response.text}")

    def login(self):
        login_url = "https://eu5.fusionsolar.huawei.com/cas/login?service=https%3A%2F%2Feu5.fusionsolar.huawei.com%2Flogin%2Fcas&locale=en_UK"
        session = requests.Session()
        login_page = session.get(login_url).text
        execution = re.search('name="execution" value="([^"]+)"', login_page).group(1)
        csrf_token = re.search('name="_csrf"\\s+value="([^"]+)"', login_page).group(1)

        session.post(
            login_url,
            data={
                "execution": execution,
                "username": self.username,
                "password": self.password,
                "_csrf": csrf_token,
                "captcha": "",
                "forceLogin": "true",
                "_eventId": "submit",
                "lt": "${loginTicket}",
            },
        )

        self.session = session.cookies.get("JSESSIONID", path="/")
        self.token = session.cookies["XSRF-TOKEN"]
        self.station = self.get_station_id()
        logging.info(
            f"Login successful, session: {self.session}, token: {self.token}, station: {self.station}"
        )

    def get_station_id(self):
        station_info = self.call_api("user/querySingleStationInfos")
        return station_info["data"]["sId"]

    def list_devices(self):
        devices = self.call_api(
            "devManager/listDev", body={"stationIds": self.station}
        )["data"]["list"]
        return [
            dev["devId"] for dev in devices if dev["devTypeId"] == "1"
        ]  # devTypeId == 1 is probably an inverter

    def get_available_signals(self, device):
        data = self.call_api(
            "signalconf/queryDevUnifiedSignals",
            body={"devId": device, "devTypeId": "1"},
        )["data"]

        return SignalSet(
            signals=[
                Signal(row["id"], row["unit"].split(".")[-1])
                for row in data
                if row["pid"] == 1
            ]
        )

    def query(self, device, date, signals):
        merged_data = {}
        for unit, subset in signals.split_by_unit().items():
            single_unit_data = self.query_single_unit(device, date, subset)
            for ts, values in single_unit_data.items():
                if ts not in merged_data:
                    merged_data[ts] = dict()
                merged_data[ts].update(values)

        return [
            Stats(ts=datetime.fromtimestamp(ts / 1000, tz=self.timezone), values=values)
            for ts, values in merged_data.items()
            if len(values) == len(signals.get_codes())
        ]

    def query_single_unit(self, device, date, signals):
        data = self.call_api(
            "devManager/queryDevHistoryData",
            body={
                "devId": device,
                "sId": self.station,
                "startTime": int(date.timestamp() * 1000),
                "signalCodes": ",".join(signals.get_codes()),
                "devTypeId": "1",
            },
        )["data"]

        return {
            int(row[0]): dict(zip(signals.get_codes(), row[2:]))
            for row in data.values()
            if row[1] != "-"
        }
