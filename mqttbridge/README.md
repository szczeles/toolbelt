# Mqtt to remote influxdb bridge

## Starting local Mosquitto

[Setting up docker on OSMC](https://gist.github.com/Peregrinox/aa55c18866a851acc9d4e03a1054485c)

    docker run -d -p 1883:1883 --name mosquitto --restart always eclipse-mosquitto

[SYS Topics](https://github.com/mqtt/mqtt.github.io/wiki/SYS-Topics)

## Reading the data

    docker exec -ti mosquitto mosquitto_sub -v -t tele/smartplug/+/+

## Smartplugs

* [Basic configuration](https://blog.koehntopp.info/2020/05/20/gosund-and-tasmota.html)
* [Flashing](https://www.malachisoord.com/2019/11/24/flashing-custom-firmware-on-a-gosund-sp111/)
* Adjust voltage: `VoltageSet 235`
* Measurement precision: `Backlog AmpRes 3; EnergyRes 5; FreqRes 3; VoltRes 3; WattRes 3`
* Reporting interval to 10s: `TelePeriod 10`
* Show voltage when toggled off: `SetOption21 1`
* Set UTC: `Timezone 0`

## Running mqtt2influxdb

    docker build -t mqtt2influxdb .
    docker run -d --restart=always --name mqttbridge mqtt2influxdb:latest --influxdb-auth $INFLUXDB_AUTH

## Deployment on k8s

    kubectl create secret generic -n mqtt mqttbridge --from-file=ca.crt=$HOME/eclipse-mosquitto-mqtt-broker-helm-chart/ca.crt --from-file=client.crt=$HOME/eclipse-mosquitto-mqtt-broker-helm-chart/client.crt --from-file=client.key=$HOME/eclipse-mosquitto-mqtt-broker-helm-chart/client.key
    docker build -t mqtt2influxdb:0.1 .
    kubectl apply -f k8s.yaml
