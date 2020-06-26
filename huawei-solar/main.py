import argparse
import logging
import pytz
import time
from datetime import datetime, timedelta

from api.pvoutput import PVOutput
from api.fusionsolar import FusionSolar

parser = argparse.ArgumentParser()
parser.add_argument('--timezone', default='Europe/Warsaw')
parser.add_argument('--fusionsolar-user')
parser.add_argument('--fusionsolar-password')
parser.add_argument('--pvoutput-api-key')
parser.add_argument('--pvoutput-system-id')
parser.add_argument('--start-date', help="Date when PV system was connected, YYYY-MM-DD format")
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s %(message)s')
logging.getLogger().setLevel(logging.INFO)

timezone = pytz.timezone(args.timezone)
pvoutput = PVOutput(args.pvoutput_system_id, args.pvoutput_api_key, timezone)
fusionsolar = FusionSolar(args.fusionsolar_user, args.fusionsolar_password, timezone)
devices = fusionsolar.list_devices()
assert len(devices) == 1, "Multiple inverters found, select a device you want to synchronize"
device = devices[0]

last_pushed_ts = pvoutput.get_last_pushed_timestamp()
logging.info(f"Last data transfer to PV Output: {last_pushed_ts}")
if last_pushed_ts is not None:
    starting_ts = last_pushed_ts
else:
    starting_ts = timezone.localize(datetime.strptime(args.start_date, '%Y-%m-%d'))
    if (timezone.localize(datetime.now()) - starting_ts).days < 14:
        logging.info(f"Starting with PV connection date: {starting_ts}")
    else:
        starting_ts = (datetime.now(timezone) - timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0)
        logging.info(f"Starting at earlist possible date, 13 days ago: {starting_ts}")

while True:
    data = fusionsolar.query(device, starting_ts)
    data_to_push = [row for row in data if row.ts > starting_ts]
    if len(data_to_push) > 0:
        logging.info(f"Pushing {len(data_to_push)} records to PVOutput")
        pvoutput.add_batch_status(data_to_push)
        starting_ts = data_to_push[-1].ts
    else:
        logging.info("No data to update")
    time.sleep(5 * 60)
