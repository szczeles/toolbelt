from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_batch


class PostgreSQL:
    def __init__(self, url):
        self.url = url
        self.conn = None

    def ensure_initialized(self):
        if self.conn is not None:
            return

        self.conn = psycopg2.connect(self.url)
        cur = self.conn.cursor()
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS energy (
            ts timestamp without time zone,
            ts_local timestamp without time zone,
            meter text,
            tariff varchar(4),
            imported integer,
            exported integer,
            primary key(ts, meter)
        )"""
        )
        self.conn.commit()

    def get_last_date(self):
        self.ensure_initialized()
        cur = self.conn.cursor()
        cur.execute("select max(ts_local) from energy")
        result = cur.fetchone()
        if result[0] is None:
            return None
        return result[0].date()

    def save(self, data):
        self.ensure_initialized()
        cur = self.conn.cursor()
        insert = "INSERT INTO energy(ts, ts_local, meter, tariff, imported, exported) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"

        execute_batch(
            cur,
            insert,
            [
                (
                    status.ts,
                    status.ts.replace(tzinfo=None),
                    status.meter.name,
                    status.meter.tariff,
                    status.imported,
                    status.exported,
                )
                for status in data
            ],
        )
        self.conn.commit()
