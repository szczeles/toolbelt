import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import pytz

from api.fusionsolar import FusionSolar, Signal, SignalSet


class TestStringMethods(unittest.TestCase):
    def setUp(self):
        self.fusionsolar = FusionSolar(
            username=None, password=None, timezone=None, region=None
        )
        self.fusionsolar.session = "session"
        self.fusionsolar.api_base = "http://api.dev"

    def _create_device_history_data(self, points):
        return {
            "data": {
                "active_power": {
                    "pmDataList": [
                        {
                            "dnId": 100,
                            "counterValue": value,
                            "startTime": ts,
                        }
                        for ts, value in points
                    ]
                }
            }
        }

    @patch("api.fusionsolar.requests.get")
    def test_queries_2_days_of_data_in_the_usual_scenario(self, get_mock):
        # given
        timezone = pytz.timezone("Europe/Warsaw")
        signals = SignalSet([Signal(id="active_power", name="Active power", unit="kW")])
        starting_ts = timezone.localize(datetime(2024, 4, 21, 18, 0, 0))
        get_mock.return_value.headers = {"Content-Type": "application/json"}
        get_mock.return_value.status_code = 200
        get_mock.return_value.json.side_effect = [
            self._create_device_history_data([(1713669300, 0.01)]),
            self._create_device_history_data([(1713756000, 0.02)]),
        ]

        # when
        data = self.fusionsolar.query(device=None, date=starting_ts, signals=signals)

        # then
        assert len(data) == 2
        assert len(get_mock.return_value.json.call_args_list) == 2

    @patch("api.fusionsolar.requests.get")
    def test_queries_more_days_in_case_of_data_gap(self, get_mock):
        # given
        timezone = pytz.timezone("Europe/Warsaw")
        signals = SignalSet([Signal(id="active_power", name="Active power", unit="kW")])
        starting_ts = timezone.localize(datetime(2024, 4, 21, 18, 0, 0))
        get_mock.return_value.headers = {"Content-Type": "application/json"}
        get_mock.return_value.status_code = 200
        get_mock.return_value.json.side_effect = [
            self._create_device_history_data([]),
            self._create_device_history_data([]),
            self._create_device_history_data([]),
            self._create_device_history_data([(1713928500, 0.03)]),
        ]

        # when
        data = self.fusionsolar.query(device=None, date=starting_ts, signals=signals)

        # then
        assert len(data) == 1
        assert len(get_mock.return_value.json.call_args_list) == 4


if __name__ == "__main__":
    unittest.main()
