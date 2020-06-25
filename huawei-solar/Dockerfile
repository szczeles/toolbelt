FROM python:3.8-slim

RUN pip install requests pytz backoff

COPY . .

ENTRYPOINT ["python3", "main.py"]
