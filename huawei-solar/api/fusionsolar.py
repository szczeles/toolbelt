import logging
import re
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

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

    def get_ids(self):
        return [signal.id for signal in self.signals]

    def get_codes(self):
        return [signal.get_code() for signal in self.signals]

@dataclass
class Signal:
    id: int
    name: str
    unit: str

    name_to_code_map = {
        'Grid phase A current': 'a_i',
        'Grid phase B current': 'b_i',
        'Grid phase C current': 'c_i',
        'Power factor': 'power_factor',
        'Grid frequency': 'elec_freq',
        'Active power': 'active_power',
        'Output reactive power': 'reactive_power',
        'Daily energy': 'day_cap',
        'Total input power': 'mppt_power',
        'PV1 input voltage': 'pv1_u',
        'PV2 input voltage': 'pv2_u',
        'PV1 input current': 'pv1_i',
        'PV2 input current': 'pv2_i',
        'Grid phase A voltage': 'a_u',
        'Grid phase B voltage': 'b_u',
        'Grid phase C voltage': 'c_u',
    }

    def __repr__(self):
        return f'{self.name} ({self.unit})'

    def get_code(self):
        return self.name_to_code_map[self.name]


class FusionSolarException(Exception):
    pass


class FusionSolar:
    def __init__(self, username, password, timezone):
        self.username = username
        self.password = password
        self.timezone = timezone
        self.session = None
        self.station = None

    @backoff.on_exception(
        backoff.expo, (requests.exceptions.RequestException, FusionSolarException)
    )
    def call_api(self, endpoint, params={}):
        url = f"https://eu5.fusionsolar.huawei.com/{endpoint}"
        response = requests.get(
            url=url,
            params=params,
            cookies={
                'bspsession': self.session
            },
            timeout=60,
        )

        if response.status_code != 200:
            raise FusionSolarException(f"Invalid response code: {response.status_code}")

        if response.headers['Content-Type'].startswith('text/html'):
            self.login()
            return self.call_api(endpoint, params)

        try:
            return response.json()
        except:
            raise FusionSolarException(f"Invalid API output: {response.text}")

    def login(self):
        login_url = "https://eu5.fusionsolar.huawei.com/unisso/login.action"
        session = requests.Session()
        session.get(login_url)

        user_validation_response = session.post(
            'https://eu5.fusionsolar.huawei.com/unisso/v2/validateUser.action',
            params={
                'service': '/unisess/v1/auth?service=%2Fnetecowebext%2Fhome%2Findex.html%23%2FLOGIN'
            },
            json={
                "organizationName": "",
                "username": self.username,
                "password": self.password,
                "verifycode": "",
                "multiRegionName": ""
            },
        )
        user_validation_result = user_validation_response.json()
        auth_result = session.get('https://eu5.fusionsolar.huawei.com' + user_validation_result['redirectURL'])
        assert auth_result.status_code == 200
        self.session = session.cookies['bspsession']
        self.station = self.get_station_id()
        logging.info(
            f"Login successful, session: {self.session}, station: {self.station}"
        )

    def get_station_id(self):
        company_info = self.call_api("rest/neteco/web/organization/v2/company/current")
        company_id = company_info['data']['moDn']
        station_info = self.call_api('rest/neteco/web/config/domain/v1/power-station/station-list', params={'params.parentDn': company_id})
        return station_info['data'][0]['dn']

    def list_devices(self):
        devices = self.call_api(
            "rest/neteco/web/config/device/v1/device-list", params={'conditionParams.parentDn': self.get_station_id()}
        )['data']
        return [
            dev["dn"] for dev in devices if dev["mocTypeName"] == "Inverter"
        ]

    def get_available_signals(self, device):
        data = self.call_api(
            "rest/pvms/web/device/v1/device-statistics-signal",
            params={'deviceDn': device}
        )['data']['signalList']
        if len(data) == 0:
            raise FusionSolarException("No signals returned")

        return SignalSet(
            signals=[
                Signal(row["id"], row["name"], row["unit"].get("unit", ""))
                for row in data
            ]
        )

    def query(self, device, date, signals):
        merged_data = {}
        for unit, subset in signals.split_by_unit().items():
            single_unit_data = self.query_single_unit_2_days(device, date, subset)
            for ts, values in single_unit_data.items():
                if ts not in merged_data:
                    merged_data[ts] = dict()
                merged_data[ts].update(values)

        for ts in merged_data.keys():
            for signal in signals.signals:
                if signal.get_code() not in merged_data[ts]:
                    merged_data[ts][signal.get_code()] = None

        return [
            Stats(ts=datetime.fromtimestamp(ts, tz=self.timezone), values=values)
            for ts, values in merged_data.items()
        ]

    def query_single_unit_2_days(self, device, date, signals):
        return {
            **self.query_single_unit(device, date.timestamp(), signals),
            **self.query_single_unit(device, date.timestamp() + 24 * 3600, signals),
        }


    def query_single_unit(self, device, timestamp, signals):
        data = self.call_api(
            "rest/pvms/web/device/v1/device-history-data",
            params={
                'signalIds': signals.get_ids(),
                'deviceDn': device,
                'date': int(timestamp * 1000)
            }
        )
        merged = defaultdict(dict)
        for signal in signals.signals:
            for sample in data['data'][str(signal.id)]['pmDataList']:
                if 'dnId' not in sample:
                    continue
                merged[sample['startTime']].update({signal.get_code(): sample['counterValue']})
        return merged
