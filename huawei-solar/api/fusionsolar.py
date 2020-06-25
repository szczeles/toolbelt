import requests
import re
from datetime import datetime
from dataclasses import dataclass
import logging
import backoff

@dataclass
class Stats:
    ts: datetime
    daily_energy: int
    current_power: int

class FusionSolarException(Exception):
    pass

class FusionSolar:
    def __init__(self, username, password, timezone):
        self.username = username
        self.password = password
        self.timezone = timezone
        self.session = None
        self.token = None
        self.station = None

    @backoff.on_exception(backoff.expo, (requests.exceptions.RequestException, FusionSolarException))
    def call_api(self, endpoint, body={}):
        url = f'https://eu5.fusionsolar.huawei.com/{endpoint}'
        response = requests.post(
            url=url,
            json=body,
            headers={'XSRF-TOKEN': self.token, 'Referer': 'https://eu5.fusionsolar.huawei.com/index.jsp'},
            cookies={'JSESSIONID': self.session}
        )

        if response.status_code != 200:
            raise FusionSolarException(f"Invalid response code: {response.status_code}")

        try:
            if response.json()['failCode'] == 306:
                self.login()
                return self.call_api(endpoint, body)
            return response.json()
        except:
            raise FusionSolarException(f"Invalid API output: {response.text}")

    def login(self):
        login_url = 'https://eu5.fusionsolar.huawei.com/cas/login?service=https%3A%2F%2Feu5.fusionsolar.huawei.com%2Flogin%2Fcas&locale=en_UK'
        session = requests.Session()
        login_page = session.get(login_url).text
        execution = re.search('name="execution" value="([^"]+)"', login_page).group(1)
        csrf_token = re.search('name="_csrf"\s+value="([^"]+)"', login_page).group(1)

        after_login = session.post(login_url, data={
            'execution': execution,
            'username': self.username,
            'password': self.password,
            '_csrf': csrf_token,
            'captcha': '',
            'forceLogin': 'true',
            '_eventId': 'submit',
            'lt': '${loginTicket}'
        })

        self.session = session.cookies.get('JSESSIONID', path='/')
        self.token = session.cookies['XSRF-TOKEN']
        self.station = self.get_station_id()
        logging.info(f"Login successful, session: {self.session}, token: {self.token}, station: {self.station}")
 
    def get_station_id(self):
        station_info = self.call_api('user/querySingleStationInfos')
        return station_info['data']['sId']

    def list_devices(self):
        devices = self.call_api('devManager/listDev', body={
            "stationIds":self.station
        })['data']['list']
        return [dev['devId'] for dev in devices if dev['devTypeId'] == '1'] # devTypeId == 1 is probably an inverter

    def query(self, device, date): 
        data = self.call_api('devManager/queryDevHistoryData', body={
            'devId': device,
            'sId': self.station,
            'startTime': int(date.timestamp() * 1000),
            'signalCodes': 'day_cap,active_power',
            'devTypeId': '1'
        })['data']

        return [
            Stats(
                ts=datetime.fromtimestamp(row[0]/1000, tz=self.timezone),
                daily_energy=int(row[2]*1000),
                current_power=int(row[3]*1000)
            ) for row in data.values() if row[1] != '-'
        ]
