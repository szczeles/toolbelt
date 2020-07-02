FROM python:3.8-slim

RUN pip install requests pytz backoff psycopg2-binary

# Temporary solution before https://github.com/influxdata/influxdb-client-python/pull/120 is released
RUN pip install https://github.com/influxdata/influxdb-client-python/archive/master.zip 

COPY . .

ENTRYPOINT ["python3", "main.py"]
