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

## Hot water pump setup

    # sets location Toruń, PL (so the sunrise/suset is calculated properly) and timezone to match DST in Poland
    Backlog Latitude 53.013790; Longitude 18.598444; Timezone 99; TimeDST 0,4,3,1,3,120; TimeSTD 0,4,10,1,3,60

    # every 30 minutes: first turn on every 5 minutes, then turn off:
    Rule1 ON Time#Minute|30 DO Backlog Power1 on; RuleTimer1 300 ENDON   ON Rules#Timer=1 DO Power1 off ENDON;
    Rule1 1

    # between 19:30 and 23:00, every 20 minutes turn on for 5 minutes:
    Rule2
      ON Time#Initialized DO Backlog var1 0 ENDON
      ON Time#Minute|20 DO Backlog var1 0; event checkbathtime=%time%; event checknight=%time%; event runpumpifneeded ENDON
      ON event#checkbathtime>=1170 DO var1 1 ENDON
      ON event#checknight>=1380 DO var1 0 ENDON
      ON event#runpumpifneeded DO Backlog Power1 %var1%; RuleTimer1 300 ENDON
      ON Rules#Timer=1 DO Power1 off ENDON;
    Rule2 1

## Running mqtt2influxdb

    docker build -t mqtt2influxdb .
    docker run -d --restart=always --name mqttbridge mqtt2influxdb:latest --influxdb-auth $INFLUXDB_AUTH

## Deployment on k8s

    kubectl create secret generic -n mqtt mqttbridge --from-file=ca.crt=$HOME/eclipse-mosquitto-mqtt-broker-helm-chart/ca.crt --from-file=client.crt=$HOME/eclipse-mosquitto-mqtt-broker-helm-chart/client.crt --from-file=client.key=$HOME/eclipse-mosquitto-mqtt-broker-helm-chart/client.key
    docker build -t mqtt2influxdb:0.1 .
    kubectl apply -f k8s.yaml
