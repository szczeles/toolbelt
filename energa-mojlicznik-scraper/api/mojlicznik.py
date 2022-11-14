import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import backoff
import pytz
import requests


@dataclass
class PowerMeter:
    id: str
    tariff: str
    code: str


@dataclass
class Status:
    ts: datetime
    meter: PowerMeter
    imported: int
    exported: int


class MojLicznikAPI:
    def __init__(self, username, password, timezone=None):
        self.username = username
        self.password = password
        self.meters = None
        if timezone is not None:
            self.timezone = timezone
        else:
            self.timezone = pytz.timezone("Europe/Warsaw")

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException)
    def login(self):
        login_url = "https://mojlicznik.energa-operator.pl/dp/UserLogin.do"
        session = requests.Session()
        login_page = session.get(login_url).text
        xsrf_token = re.search('name="_antixsrf"\\s+value="([^"]+)"', login_page).group(
            1
        )

        main_page = session.post(
            login_url,
            data={
                "selectedForm": 1,
                "save": "save",
                "rememberMe": "on",
                "loginNow": "sdffdsfs",
                "j_username": self.username,
                "j_password": self.password,
                "_antixsrf": xsrf_token,
            },
        )

        self.session = session.cookies["JSESSIONID"]
        self.meters = [
            PowerMeter(*meter)
            for meter in re.findall(
                "{\\s+id: (\\d+),\\s+ppe: '[^']+',\\s+tmp: '1',\\s+tariffCode: '([^']+)',\\s+name: '([^']+)'\\s+}",
                main_page.text,
            )
        ]
        if len(self.meters) == 0:
            print(main_page.content)
        logging.info(
            "Login successful! Session: %s, power meters: %s", self.session, self.meters
        )

    def get_meters(self):
        if self.meters is None:
            self.login()

        return self.meters

    def get_timestamp_millis(self, date):
        return (
            int(
                self.timezone.localize(
                    datetime.combine(date, datetime.min.time())
                ).timestamp()
            )
            * 1000
        )

    def get_data_for_days(self, power_meter, start_date, end_date):
        results = []
        for date in [
            start_date + timedelta(n) for n in range((end_date - start_date).days + 1)
        ]:
            data_for_day = self.get_data_for_day(power_meter, date)
            if data_for_day and len(data_for_day) != 24:
                logging.warning(
                    f"Missing {24 - len(data_for_day)} entires for day {date}"
                )
            results.extend(data_for_day)
        return results

    def get_data_for_day(self, power_meter, date):
        logging.info(
            "Getting data for power meter %s for date %s", power_meter.code, date
        )
        imported = self.call_api(power_meter, date, "A+")
        exported = self.call_api(power_meter, date, "A-")
        common_keys = set(imported.keys()) & set(exported.keys())
        return [
            Status(
                ts=datetime.fromtimestamp(ts / 1000, self.timezone),
                meter=power_meter,
                imported=int(imported[ts] * 1000) if imported[ts] is not None else None,
                exported=int(exported[ts] * 1000) if exported[ts] is not None else None,
            )
            for ts in sorted(common_keys)
        ]

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException)
    def call_api(self, power_meter, date, mode):
        response = requests.get(
            "https://mojlicznik.energa-operator.pl/dp/resources/chart",
            params={
                "mainChartDate": self.get_timestamp_millis(date),
                "type": "DAY",
                "meterPoint": power_meter.id,
                "mo": mode,
            },
            cookies={"JSESSIONID": self.session},
            timeout=1.0,
        )
        if response.headers["Content-Type"] != "application/json":
            logging.warning("Invalid API response, re-login and retry")
            self.login()
            return self.call_api(power_meter, date, mode)
        return {
            int(f["tm"]): f["zones"][0]
            for f in response.json()["response"]["mainChart"]
        }
