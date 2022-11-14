import datetime
import hashlib
from dataclasses import dataclass

import backoff
import requests
from dateutil.parser import parse


@dataclass
class Status:
    ts: datetime.datetime
    current_power_w: int = 0
    daily_energy_wh: int = 0


class FoxEssApi:
    def __init__(self, username, password):
        self.username = username
        self.password = hashlib.md5(password.encode()).hexdigest()
        self.token = None
        self.current_station = None

    def get_data_since(self, ts: datetime.datetime):
        date_to_fetch = ts.date()
        entries = []
        while True:
            entries.extend(self.get_data_for_day(date_to_fetch))
            date_to_fetch += datetime.timedelta(1)
            if date_to_fetch > datetime.date.today():
                break

        return [e for e in entries if e.ts > ts]

    def get_data_for_day(self, dt: datetime.date):
        values = {}

        data = self._call_api(
            "c/v0/plant/history/raw",
            json={
                "stationID": self.current_station,
                "variables": ["generationPower", "feedinPower", "loadsPower"],
                "timespan": "day",
                "beginDate": {
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                    "hour": 0,
                    "minute": 0,
                    "second": 0,
                },
            },
        )
        results = next(
            r["data"]
            for r in data.json()["result"]
            if r["variable"] == "generationPower"
        )

        for line in results:
            ts = parse(line["time"])
            ts = ts.replace(tzinfo=None)
            if line["value"] == 0:
                continue

            status = Status(ts=ts)
            status.current_power_w = int(line["value"] * 1000)
            values[ts] = status

        data = self._call_api(
            "c/v0/plant/history/report",
            json={
                "stationID": self.current_station,
                "reportType": "day",
                "variables": ["generation"],
                "queryDate": {
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                    "hour": 0,
                },
            },
        )
        results = data.json()["result"][0]["data"]
        current_sum = 0
        for line in results:
            if line["value"] == 0:
                continue
            current_sum += int(round(line["value"], 2) * 1000)
            hour = line["index"]
            marked = False
            for ts in values:
                if ts.hour == hour:
                    values[ts].daily_energy_wh = current_sum
                    marked = True

            if not marked and dt < datetime.date.today():
                ts = datetime.datetime(dt.year, dt.month, dt.day, hour)
                status = Status(ts=ts)
                status.daily_energy_wh = current_sum
                values[ts] = status

        return [values[ts] for ts in sorted(values.keys())]

    def set_current_station(self, station_id):
        self.current_station = station_id

    def _login(self):
        resp = requests.post(
            "https://www.foxesscloud.com/c/v0/user/login",
            json={"user": self.username, "password": self.password},
        )
        assert (
            resp.status_code == 200
        ), f"Non 200 response from login: {resp.status_code}, {resp.text}"
        self.token = resp.json()["result"]["token"]

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException)
    def _call_api(self, url, json=None):
        response = self._call_api_raw(url, json)
        if response.json().get("result") is None:
            print("Result is none, need to re-login")
            self._login()
            response = self._call_api_raw(url, json)
        return response

    def _call_api_raw(self, url, json=None):
        if self.token is None:
            self._login()
        if json is None:
            return requests.get(
                f"https://www.foxesscloud.com/{url}", headers={"token": self.token}
            )
        else:
            return requests.post(
                f"https://www.foxesscloud.com/{url}",
                headers={"token": self.token},
                json=json,
            )

    def list_stations(self):
        return self._call_api("c/v0/plant/droplist").json()["result"]["plants"]
