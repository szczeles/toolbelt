import base64
import codecs
import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import backoff
import requests

import pkcs1
import rsa


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
        "Grid phase A current": "a_i",
        "Grid phase B current": "b_i",
        "Grid phase C current": "c_i",
        "Power factor": "power_factor",
        "Grid frequency": "elec_freq",
        "Active power": "active_power",
        "Output reactive power": "reactive_power",
        "Daily energy": "day_cap",
        "Total input power": "mppt_power",
        "PV1 input voltage": "pv1_u",
        "PV2 input voltage": "pv2_u",
        "PV3 input voltage": "pv3_u",
        "PV4 input voltage": "pv4_u",
        "PV1 input current": "pv1_i",
        "PV2 input current": "pv2_i",
        "PV3 input current": "pv3_i",
        "PV4 input current": "pv4_i",
        "Grid phase A voltage": "a_u",
        "Grid phase B voltage": "b_u",
        "Grid phase C voltage": "c_u",
        "MPPT 1 DC cumulative energy": "mppt_1_cap",
        "MPPT 2 DC cumulative energy": "mppt_2_cap",
        "Grid voltage": "grid_voltage",
        "Grid current": "grid_current",
    }

    def __repr__(self):
        return f"{self.name} ({self.unit})"

    def get_code(self):
        return self.name_to_code_map[self.name]


class FusionSolarException(Exception):
    pass


class FusionSolar:
    def __init__(self, username, password, timezone, region, station_id=None):
        self.username = username
        self.password = password
        self.timezone = timezone
        self.region = region
        self.station_id = station_id
        self.session = None
        self.station = None
        self.api_base = None
        self.csrf_token = None

    @backoff.on_exception(
        backoff.expo, (requests.exceptions.RequestException, FusionSolarException)
    )
    def call_api(self, endpoint, method="get", params={}):
        if self.session is None or self.api_base is None:
            self.login()

        url = f"{self.api_base}/{endpoint}"
        func = getattr(requests, method)
        response = func(
            url=url,
            params=params if method == "get" else None,
            cookies={"dp-session": self.session},
            timeout=60,
            json=params if method == "post" else None,
        )

        if response.headers["Content-Type"].startswith("text/html"):
            self.login()
            return self.call_api(endpoint, params)

        if response.status_code != 200:
            raise FusionSolarException(
                f"Invalid response code: {response.status_code}, content: {response.text}"
            )

        try:
            return response.json()
        except:
            raise FusionSolarException(f"Invalid API output: {response.text}")

    def login(self):
        login_url = f"https://{self.region}.fusionsolar.huawei.com/unisso/login.action"
        session = requests.Session()
        login_page = session.get(login_url).text
        assert (
            "ssoCredentials.verifyCode" not in login_page
        ), "Captha enabled on login page, try again later"

        pubkey = session.get(
            f"https://{self.region}.fusionsolar.huawei.com/unisso/pubkey"
        ).json()
        if not pubkey["enableEncrypt"]:
            raise NotImplementedError("Is there a region with no ecryption enabled?")
        else:
            key = rsa.PublicKey.load_pkcs1_openssl_pem(pubkey["pubKey"].encode("ascii"))
            encrypted_password = base64.b64encode(
                pkcs1.rsaes_oaep.encrypt(
                    pkcs1.keys.RsaPublicKey(key.n, key.e),
                    self.password.encode("utf-8"),
                    hash_class=hashlib.sha384,
                )
            ).decode("ascii")
            user_validation_response = session.post(
                f"https://{self.region}.fusionsolar.huawei.com/unisso/v3/validateUser.action",
                params={
                    "service": "/unisess/v1/auth?service=%2Fnetecowebext%2Fhome%2Findex.html",
                    "timeStamp": pubkey["timeStamp"],
                    "nonce": codecs.encode(
                        encrypted_password[:16].encode("ascii"), "hex"
                    ).decode(),
                },
                json={
                    "organizationName": "",
                    "username": self.username,
                    "password": encrypted_password + pubkey["version"],
                },
            )

        user_validation_result = user_validation_response.json()
        assert user_validation_result["errorMsg"] is None
        assert (
            user_validation_result["errorCode"] == "470"
        )  # 470 seems like "successful login"
        url = (
            f"https://{self.region}.fusionsolar.huawei.com"
            + user_validation_result["respMultiRegionName"][-1]
        )
        api_server_redirect = session.get(url)
        self.api_base = f"https://{urlparse(api_server_redirect.url).netloc}"
        self.session = session.cookies["dp-session"]
        self.station = self.station_id or self.get_station_id()
        logging.info(
            f"Login successful, session: {self.session}, station: {self.station}"
        )

    def get_station_id(self):
        station_info = self.call_api(
            "rest/pvms/web/station/v1/station/station-list",
            method="post",
            params={
                "curPage": 1,
                "pageSize": 10,
                "gridConnectedTime": "",
                "queryTime": 1666044000000,
                "timeZone": 2,
                "sortId": "createTime",
                "sortDir": "DESC",
                "locale": "en_US",
            },
        )
        logging.debug("Station info: %s", station_info["data"])
        return station_info["data"]["list"][0]["dn"]

    def list_devices(self):
        devices = self.call_api(
            "rest/neteco/web/config/device/v1/device-list",
            params={
                "conditionParams.parentDn": self.station_id or self.get_station_id()
            },
        )["data"]
        logging.debug("Devices: %s", devices)
        return [dev["dn"] for dev in devices if dev["mocTypeName"] == "Inverter"]

    def get_available_signals(self, device):
        data = self.call_api(
            "rest/pvms/web/device/v1/device-statistics-signal",
            params={"deviceDn": device},
        )["data"]["signalList"]
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
                "signalIds": signals.get_ids(),
                "deviceDn": device,
                "date": int(timestamp * 1000),
            },
        )
        logging.debug(
            "Single unit data for device %s, timestamp %s and signals %s: %s",
            device,
            timestamp,
            signals,
            data,
        )
        merged = defaultdict(dict)
        for signal in signals.signals:
            for sample in data["data"][str(signal.id)]["pmDataList"]:
                if "dnId" not in sample:
                    continue
                merged[sample["startTime"]].update(
                    {signal.get_code(): sample["counterValue"]}
                )
        return merged
