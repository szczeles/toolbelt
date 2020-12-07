FROM python:3.8-slim

RUN pip install requests pytz backoff psycopg2-binary influxdb-client==1.11.0

COPY . .

ENTRYPOINT ["python3", "main.py"]
