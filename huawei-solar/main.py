import argparse
import logging
import time
from datetime import datetime, timedelta

import pytz

from api.fusionsolar import FusionSolar
from api.pvoutput import PVOutput
from db.influxdb import InfluxDB
from db.postgres import PostgreSQL

parser = argparse.ArgumentParser()
parser.add_argument("--timezone", default="Europe/Warsaw")
parser.add_argument("--fusionsolar-user", required=True)
parser.add_argument("--fusionsolar-password", required=True)
parser.add_argument(
    "--fusionsolar-region", default="intlobt"
)  # automatic server selection: https://forum.huawei.com/enterprise/en/forum.php?mod=redirect&goto=findpost&ptid=707527&pid=3828837
parser.add_argument("--pvoutput-api-key", required=True)
parser.add_argument("--pvoutput-system-id", required=True)
parser.add_argument("--postgres-url", required=False)
parser.add_argument("--influxdb-url", required=False)
parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
parser.add_argument(
    "--start-date",
    help="Date when PV system was connected, YYYY-MM-DD format",
    required=False,
)
args = parser.parse_args()

logging.basicConfig(format="%(asctime)s %(message)s")
logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)

timezone = pytz.timezone(args.timezone)
fusionsolar = FusionSolar(
    args.fusionsolar_user,
    args.fusionsolar_password,
    timezone,
    region=args.fusionsolar_region,
)
devices = fusionsolar.list_devices()
assert (
    len(devices) == 1
), "Multiple inverters found, select a device you want to synchronize"
device = devices[0]
signals = fusionsolar.get_available_signals(device)
logging.info("Available signals: %s", signals)
pvoutput = PVOutput(args.pvoutput_system_id, args.pvoutput_api_key, timezone)
outputs = [("PVOutput", pvoutput)]
if args.postgres_url is not None:
    outputs.insert(0, ("PostgreSQL", PostgreSQL(args.postgres_url, signals)))
if args.influxdb_url is not None:
    outputs.insert(0, ("InfluxDB", InfluxDB(args.influxdb_url)))

last_pushed_ts = pvoutput.get_last_pushed_timestamp()
logging.info(f"Last data transfer to PV Output: {last_pushed_ts}")
if last_pushed_ts is not None:
    starting_ts = last_pushed_ts
else:
    starting_ts = timezone.localize(datetime.strptime(args.start_date, "%Y-%m-%d"))
    if (timezone.localize(datetime.now()) - starting_ts).days < 14:
        logging.info(f"Starting with PV connection date: {starting_ts}")
    else:
        starting_ts = (datetime.now(timezone) - timedelta(days=13)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        logging.info(f"Starting at earlist possible date, 13 days ago: {starting_ts}")

while True:
    data = fusionsolar.query(device, starting_ts, signals)
    data_to_push = [row for row in data if row.ts > starting_ts]
    if len(data_to_push) > 0:
        for output in outputs:
            logging.info(f"Pushing {len(data_to_push)} records to {output[0]}")
            output[1].save(data_to_push)
        starting_ts = data_to_push[-1].ts
    else:
        logging.info("No data to update")
    time.sleep(5 * 60)
