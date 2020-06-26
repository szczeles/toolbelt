from dataclasses import dataclass
from datetime import datetime

import backoff
import requests


class PVOutputException(Exception):
    pass


class PVOutputUnrecoverableException(Exception):
    pass


class PVOutputBadRequestException(Exception):
    pass


@dataclass
class Status:
    ts: datetime
    energy_generation: int
    power_generation: int
    energy_consumption: int
    power_consumption: int
    normalised_output: int
    temperature: float
    voltage: float

    @staticmethod
    def parse(statusline, timezone):
        parts = statusline.split(",")
        return Status(
            ts=timezone.localize(datetime.strptime(parts[0] + parts[1], "%Y%m%d%H:%M")),
            energy_generation=int(parts[2]),
            power_generation=int(parts[3]),
            energy_consumption=int(parts[4]) if parts[4] != "NaN" else None,
            power_consumption=int(parts[5]) if parts[5] != "NaN" else None,
            normalised_output=float(parts[6]),
            temperature=float(parts[7]) if parts[7] != "NaN" else None,
            voltage=float(parts[8]) if parts[8] != "NaN" else None,
        )
        print(statusline, timezone)


class PVOutput:
    def __init__(self, system_id, api_key, timezone):
        self.system_id = system_id
        self.api_key = api_key
        self.timezone = timezone

    @backoff.on_exception(
        backoff.expo, (requests.exceptions.RequestException, PVOutputException)
    )
    def call_api(self, endpoint, params={}):
        url = f"https://pvoutput.org/service/r2/{endpoint}.jsp"
        response = requests.get(
            url,
            headers={
                "X-Pvoutput-Apikey": self.api_key,
                "X-Pvoutput-SystemId": str(self.system_id),
            },
            params=params,
        )
        if response.status_code == 400:
            raise PVOutputBadRequestException(response.text)
        if response.status_code == 401:
            raise PVOutputUnrecoverableException(response.text)
        if response.status_code != 200:
            raise PVOutputException(response.text)
        return response

    def get_status(self, date=None):
        data = self.call_api("getstatus", {"d": date}).text
        return Status.parse(data, self.timezone)

    def get_last_pushed_timestamp(self):
        try:
            return self.get_status().ts
        except PVOutputBadRequestException:
            return None

    def add_batch_status(self, statuses):
        chunk_size = 30
        for chunk in [
            statuses[i : i + chunk_size] for i in range(0, len(statuses), chunk_size)
        ]:
            data = ";".join(
                [
                    f'{s.ts.strftime("%Y%m%d")},{s.ts.strftime("%H:%M")},{s.daily_energy},{s.current_power}'
                    for s in chunk
                ]
            )
            self.call_api("addbatchstatus", {"data": data})
