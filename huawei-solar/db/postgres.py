import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch

from model import Output


class PostgreSQL(Output):
    def __init__(self, url, signals):
        self.url = url
        self.signals = signals
        self.conn = None

    def ensure_initialized(self):
        if self.conn is not None:
            return

        self.conn = psycopg2.connect(self.url)
        cur = self.conn.cursor()
        fields = [f"{code} decimal(7, 3)" for code in self.signals.get_codes()]
        cur.execute(
            f"""
        CREATE TABLE IF NOT EXISTS pv (
            ts timestamp without time zone primary key,
            ts_local timestamp without time zone,
            {','.join(fields)}
        )"""
        )
        self.conn.commit()

    def save(self, data):
        self.ensure_initialized()
        cur = self.conn.cursor()
        columns = ["ts", "ts_local"] + self.signals.get_codes()
        insert = sql.SQL(
            "INSERT INTO pv({}) VALUES ({}) ON CONFLICT DO NOTHING"
        ).format(
            sql.SQL(", ").join(map(sql.Identifier, [c.lower() for c in columns])),
            sql.SQL(", ").join(map(sql.Placeholder, columns)),
        )

        execute_batch(
            cur,
            insert,
            [
                {**row.values, "ts": row.ts, "ts_local": row.ts.replace(tzinfo=None)}
                for row in data
            ],
        )
        self.conn.commit()
