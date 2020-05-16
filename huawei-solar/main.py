import argparse
import logging
import pytz
import time

from api.pvoutput import PVOutput
from api.fusionsolar import FusionSolar

parser = argparse.ArgumentParser()
parser.add_argument('--timezone', default='Europe/Warsaw')
parser.add_argument('--fusionsolar-user')
parser.add_argument('--fusionsolar-password')
parser.add_argument('--pvoutput-api-key')
parser.add_argument('--pvoutput-system-id')
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

while True:
    data = fusionsolar.query(device, last_pushed_ts)
    data_to_push = [row for row in data if row.ts > last_pushed_ts]
    if len(data_to_push) > 0:
        logging.info(f"Pushing {len(data_to_push)} records to PVOutput")
        pvoutput.add_batch_status(data_to_push)
        last_pushed_ts = data_to_push[-1].ts

    logging.info("No data to update")
    time.sleep(5 * 60)
