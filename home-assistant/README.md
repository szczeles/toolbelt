# Home assistant config

Front X-mas lights control

## Mosquitto broker

    sudo apt install mosquitto mosquitto-clients

## Home assistant

    docker run --init --restart=always -d --name="home-assistant" -e "TZ=Europe/Warsaw" -v /srv/homeassistant-config:/config --net=host homeassistant/raspberrypi3-homeassistant:latest
