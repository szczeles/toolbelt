from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


class InfluxDB:
    def __init__(self, uri):
        self.uri = uri
        self.bucket = "energy/autogen"
        self.client = None

    def ensure_initialized(self):
        if self.client is not None:
            return

        self.client = InfluxDBClient(url=self.uri, org="-", token="-")

    def get_last_date(self):
        raise NotImplementedError()

    def save(self, data):
        self.ensure_initialized()

        points = [
            Point.from_dict(
                {
                    "measurement": "energy",
                    "fields": {
                        "meter": status.meter.name,
                        "tariff": status.meter.tariff,
                        "imported": status.imported,
                        "exporeted": status.exported,
                    },
                    "time": status.ts,
                }
            )
            for status in data
        ]
        self.client.write_api(write_options=SYNCHRONOUS).write(
            bucket=self.bucket, record=points
        )
