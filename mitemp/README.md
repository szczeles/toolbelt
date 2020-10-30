# LYWSD03MMC to MQTT

## Build

    docker build -t mitemp2mqtt .

## Run

    docker run --net=host -e SENSOR_MAC=A4:C1:38:F6:52:79 -e SENSOR_NAME=salon --restart=always --name mitemp-salon -d mitemp2mqtt
    docker run --net=host -e SENSOR_MAC=A4:C1:38:0E:CB:17 -e SENSOR_NAME=gabinet --restart=always --name mitemp-gabinet -d mitemp2mqtt
