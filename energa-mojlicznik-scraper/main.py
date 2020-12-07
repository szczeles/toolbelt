import argparse
import logging
from datetime import date, datetime, timedelta

from api.mojlicznik import MojLicznikAPI
from db.influxdb import InfluxDB
from db.postgres import PostgreSQL

parser = argparse.ArgumentParser()
parser.add_argument("--mojlicznik-user")
parser.add_argument("--mojlicznik-password")
parser.add_argument("--postgres-url", required=False)
parser.add_argument("--influxdb-url", required=False)

args = parser.parse_args()

logging.basicConfig(format="%(asctime)s %(message)s")
logging.getLogger().setLevel(logging.INFO)

ml = MojLicznikAPI(args.mojlicznik_user, args.mojlicznik_password)
dbs = []
if args.influxdb_url is not None:
    dbs.append(("InfluxDB", InfluxDB(args.influxdb_url)))
if args.postgres_url is not None:
    dbs.append(("PostgreSQL", PostgreSQL(args.postgres_url)))

db_last_date = dbs[-1][1].get_last_date()
logging.info("Last date for %s is %s", dbs[-1][0], db_last_date)
if db_last_date is None:
    start_date = (datetime.now() - timedelta(days=366 * 2)).date()
else:
    start_date = db_last_date

logging.info("Start date: %s", start_date)
for meter in ml.get_meters():
    data = ml.get_data_for_days(meter, start_date, date.today())
    for db in dbs:
        logging.info("Saving %d records to %s", len(data), db[0])
        db[1].save(data)
