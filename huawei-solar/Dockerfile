FROM python:3.11-slim

RUN pip install --no-cache --disable-pip-version-check requests pytz backoff psycopg2-binary influxdb-client==1.16.0 rsa==4.9 pkcs1==0.9.7 'urllib3<2'

COPY . .

ENTRYPOINT ["python3", "main.py"]
