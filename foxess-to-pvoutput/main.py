import argparse
import logging
import time
from datetime import datetime

from foxess import FoxEssApi
from pvoutput import PVOutput

parser = argparse.ArgumentParser()
parser.add_argument("--foxess-user", required=True)
parser.add_argument("--foxess-password", required=True)
parser.add_argument("--pvoutput-api-key", required=True)
parser.add_argument("--pvoutput-system-id", required=True)
parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
parser.add_argument(
    "--start-date",
    help="Date when PV system was connected, YYYY-MM-DD format",
    required=False,
)
args = parser.parse_args()


logging.basicConfig(format="%(asctime)s %(message)s")
logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)


api = FoxEssApi(args.foxess_user, args.foxess_password)
stations = api.list_stations()
assert len(stations) == 1
api.set_current_station(stations[0]["stationID"])

pvoutput = PVOutput(args.pvoutput_system_id, args.pvoutput_api_key)


last_pushed_ts = pvoutput.get_last_pushed_timestamp()
logging.info(f"Last data transfer to PV Output: {last_pushed_ts}")
if last_pushed_ts is not None:
    starting_ts = last_pushed_ts
else:
    starting_ts = datetime.strptime(args.start_date, "%Y-%m-%d")

while True:
    data_to_push = api.get_data_since(starting_ts)
    if len(data_to_push) > 0:
        logging.info(f"Pushing {len(data_to_push)} records to PVOutput")
        pvoutput.save(data_to_push)
        starting_ts = data_to_push[-1].ts
    else:
        logging.info("No data to update")
    time.sleep(10 * 60)
