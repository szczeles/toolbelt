from influxdb_client import InfluxDBClient, Point

from model import Output


class InfluxDB(Output):
    def __init__(self, uri):
        self.uri = uri
        self.bucket = "pv/infinity"
        self.api = None

    def ensure_initialized(self):
        if self.api is not None:
            return

        client = InfluxDBClient(url=self.uri, org="-", token="-")
        self.api = client.write_api()

    def save(self, data):
        self.ensure_initialized()

        for row in data:
            point = Point.from_dict(
                {"measurement": "inverter", "fields": row.values, "time": row.ts}
            )
            self.api.write(bucket=self.bucket, record=point)
