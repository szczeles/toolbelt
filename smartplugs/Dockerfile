FROM python:3.8-slim

RUN pip install paho-mqtt==1.5.1 influxdb-client==1.11.0 

COPY main.py main.py

ENTRYPOINT ["python3", "-u", "main.py"]
