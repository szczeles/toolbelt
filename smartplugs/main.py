import logging
import json
import argparse

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, Configuration
from influxdb_client.client.write_api import SYNCHRONOUS


influxdb_client = None
args = None

def on_connect(client, userdata, flags, rc):
    logging.info('Connected with result code %d', rc)
    client.subscribe(args.mqtt_topic)


def on_message(client, userdata, msg):
    if msg.topic.endswith('STATE'):
        point = parse_state_msg(msg.topic, json.loads(msg.payload.decode('utf-8')))
    elif msg.topic.endswith('SENSOR'):
        point = parse_sensor_msg(msg.topic, json.loads(msg.payload.decode('utf-8')))
    else:
        return

    push_to_influxdb(point)

def parse_state_msg(topic, msg):
    return Point.measurement('smartplugstate').time(msg['Time']).tag('spid', int(topic.split('/')[2])) \
            .field('uptime_sec', msg['UptimeSec']) \
            .field('heap', msg['Heap']) \
            .field('sleep_mode', msg['SleepMode']) \
            .field('sleep', msg['Sleep']) \
            .field('loadavg', msg['LoadAvg']) \
            .field('mqtt_count', msg['MqttCount']) \
            .field('power', msg['POWER']) \
            .field('is_on', msg['POWER'] == 'ON') \
            .field('wifi_channel', msg['Wifi']['Channel']) \
            .field('wifi_rssi', msg['Wifi']['RSSI']) \
            .field('wifi_signal', msg['Wifi']['Signal']) \
            .field('wifi_link_count', msg['Wifi']['LinkCount']) \

def parse_sensor_msg(topic, msg):
    time = msg['Time']
    msg = msg['ENERGY']
    return Point.measurement('smartplugsensor').time(time).tag('spid', int(topic.split('/')[2])) \
            .field('total_start_time', msg['TotalStartTime']) \
            .field('total', msg['Total']) \
            .field('yesterday', msg['Yesterday']) \
            .field('today', msg['Today']) \
            .field('period', msg['Period']) \
            .field('power', msg['Power']) \
            .field('apparent_power', msg['ApparentPower']) \
            .field('reactive_power', msg['ReactivePower']) \
            .field('factor', msg['Factor']) \
            .field('voltage', msg['Voltage']) \
            .field('current', msg['Current']) \

def push_to_influxdb(point):
    influxdb_client.write_api(write_options=SYNCHRONOUS).write(bucket='mqtt/autogen', record=point)

if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--influxdb-url", default='https://influxdb.mlops.eu')
    parser.add_argument("--influxdb-auth", required=True)
    parser.add_argument("--mqtt-topic", default='tele/smartplug/+/+')
    parser.add_argument("--mqtt-client-id", default='MQTTInfluxDBBridge')
    parser.add_argument("--mqtt-host", default='192.168.0.192')
    parser.add_argument("--mqtt-port", type=int, default=1883)
    args = parser.parse_args()
    logging.info('Starting MQTT to InfluxDB bridge, %s', args)

    influxdb_client = InfluxDBClient(url=args.influxdb_url, token="-", org="-")
    influxdb_client.api_client.default_headers['Authorization'] = f'Basic {args.influxdb_auth}'

    mqtt_client = mqtt.Client(args.mqtt_client_id)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(args.mqtt_host, args.mqtt_port)
    mqtt_client.loop_forever()
