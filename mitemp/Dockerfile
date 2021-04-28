FROM python:3.8-slim

RUN apt update && \
    apt install -y mosquitto-clients build-essential libglib2.0-0 libglib2.0-dev psmisc --no-install-recommends && \
    pip install bluepy && \
    apt purge -y build-essential libglib2.0-dev && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /app
ADD https://raw.githubusercontent.com/JsBergbau/MiTemperature2/master/LYWSD03MMC.py /app/LYWSD03MMC.py
COPY send_to_mqtt.sh /app/send_to_mqtt.sh

ENTRYPOINT ["bash", "-c", "python3 -u /app/LYWSD03MMC.py --device $SENSOR_MAC -r -b 100 --skipidentical 50 --debounce --callback send_to_mqtt.sh"]
