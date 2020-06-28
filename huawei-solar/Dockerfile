FROM python:3.8-slim

RUN pip install requests pytz backoff psycopg2-binary

COPY . .

ENTRYPOINT ["python3", "main.py"]
