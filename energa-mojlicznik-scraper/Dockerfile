FROM python:3.11-slim

RUN pip install requests pytz backoff psycopg2-binary influxdb-client==1.16.0

COPY . .

ENTRYPOINT ["python3", "main.py"]
