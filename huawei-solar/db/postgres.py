import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch

from db.model import PvDB


class PostgreSQL(PvDB):
    def __init__(self, uri, signals):
        self.uri = uri
        self.signals = signals
        self.conn = None

    def ensure_initialized(self):
        if self.conn is not None:
            return

        self.conn = psycopg2.connect(self.uri)
        cur = self.conn.cursor()
        fields = [f"{code} decimal(7, 3)" for code in self.signals.get_codes()]
        cur.execute(
            f"""
        CREATE TABLE IF NOT EXISTS pv (
            ts timestamp without time zone primary key,
            {','.join(fields)}
        )"""
        )
        self.conn.commit()

    def save(self, data):
        self.ensure_initialized()
        cur = self.conn.cursor()
        columns = ["ts"] + self.signals.get_codes()
        insert = sql.SQL(
            "INSERT INTO pv({}) VALUES ({}) ON CONFLICT DO NOTHING"
        ).format(
            sql.SQL(", ").join(map(sql.Identifier, [c.lower() for c in columns])),
            sql.SQL(", ").join(map(sql.Placeholder, columns)),
        )

        execute_batch(
            cur,
            insert,
            [{**row.values, "ts": row.ts.replace(tzinfo=None)} for row in data],
        )
        self.conn.commit()
