import argparse
import json
import logging
import queue
import threading
from datetime import datetime

import backoff
import pytz
from influxdb_client import Configuration, InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

import paho.mqtt.client as mqtt

influxdb_pusher = None
args = None


def parse_time(time):
    return pytz.timezone("Europe/Warsaw").localize(datetime.fromisoformat(time))


def on_connect(client, userdata, flags, rc):
    logging.info("Connected with result code %d", rc)
    client.subscribe(args.mqtt_topic)


def on_message_handling_exceptions(client, userdata, msg):
    try:
        on_message(client, userdata, msg)
    except:
        logging.exception("Unable to process %s: %s", msg.topic, msg.payload)


def on_message(client, userdata, msg):
    if msg.topic == "tele/ecoal/STATE":
        return  # not using ecoal anymore :-)

    if msg.topic.endswith("STATE"):
        point = parse_state_msg(msg.topic, json.loads(msg.payload.decode("utf-8")))
    elif msg.topic.endswith("SENSOR"):
        point = parse_sensor_msg(msg.topic, json.loads(msg.payload.decode("utf-8")))
    elif msg.topic.startswith("tele/temp"):
        point = parse_mitemp_msg(msg.topic, json.loads(msg.payload.decode("utf-8")))
    else:
        return

    influxdb_pusher.write(point)


def parse_mitemp_msg(topic, msg):
    sensor_name = topic.split("/")[-1]
    return (
        Point.measurement("mitemperature")
        .time(datetime.fromtimestamp(msg["timestamp"]))
        .tag("room", sensor_name)
        .field("temperature", msg["temperature"])
        .field("humidity", msg["humidity"])
        .field("batt_voltage", msg["batt_voltage"])
        .field("batt_level", msg["batt_level"])
    )


def parse_state_msg(topic, msg):
    return (
        Point.measurement("smartplugstate")
        .time(parse_time(msg["Time"]))
        .tag("spid", int(topic.split("/")[2]))
        .field("uptime_sec", msg["UptimeSec"])
        .field("heap", msg["Heap"])
        .field("sleep_mode", msg["SleepMode"])
        .field("sleep", msg["Sleep"])
        .field("loadavg", msg["LoadAvg"])
        .field("mqtt_count", msg["MqttCount"])
        .field("power", msg["POWER"])
        .field("is_on", msg["POWER"] == "ON")
        .field("wifi_channel", msg["Wifi"]["Channel"])
        .field("wifi_rssi", msg["Wifi"]["RSSI"])
        .field("wifi_signal", msg["Wifi"]["Signal"])
        .field("wifi_link_count", msg["Wifi"]["LinkCount"])
    )


def parse_sensor_msg(topic, msg):
    time = parse_time(msg["Time"])
    msg = msg["ENERGY"]
    return (
        Point.measurement("smartplugsensor")
        .time(time)
        .tag("spid", int(topic.split("/")[2]))
        .field("total_start_time", msg["TotalStartTime"])
        .field("total", msg["Total"])
        .field("yesterday", msg["Yesterday"])
        .field("today", msg["Today"])
        .field("period", msg["Period"])
        .field("power", msg["Power"])
        .field("apparent_power", msg["ApparentPower"])
        .field("reactive_power", msg["ReactivePower"])
        .field("factor", msg["Factor"])
        .field("voltage", msg["Voltage"])
        .field("current", msg["Current"])
    )


class InfluxAsyncPusher(threading.Thread):
    def __init__(self, args):
        super().__init__()
        self.client = InfluxDBClient(url=args.influxdb_url, token="-", org="-")
        self.queue = queue.Queue()

    def write(self, point):
        self.queue.put(point)

    @backoff.on_exception(backoff.expo, Exception)
    def push(self, point):
        self.client.write_api(write_options=SYNCHRONOUS).write(
            bucket="mqtt/autogen", record=point
        )

    def run(self):
        while True:
            self.push(self.queue.get())
            self.queue.task_done()


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--influxdb-url", default="http://influxdb.iot.svc:8086")
    parser.add_argument("--mqtt-topic", default="tele/#")
    parser.add_argument("--mqtt-client-id", default="MQTTInfluxDBBridge")
    parser.add_argument("--mqtt-host", default="mosquitto-internal")
    parser.add_argument("--mqtt-port", type=int, default=1884)
    parser.add_argument("--mqtt-ca-crt")
    parser.add_argument("--mqtt-client-crt")
    parser.add_argument("--mqtt-client-key")
    args = parser.parse_args()
    logging.info("Starting MQTT to InfluxDB bridge, %s", args)

    influxdb_pusher = InfluxAsyncPusher(args)
    influxdb_pusher.start()

    mqtt_client = mqtt.Client(args.mqtt_client_id)
    if args.mqtt_ca_crt and args.mqtt_client_crt and args.mqtt_client_key:
        mqtt_client.tls_set(
            args.mqtt_ca_crt,
            args.mqtt_client_crt,
            args.mqtt_client_key,
        )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message_handling_exceptions
    mqtt_client.connect(args.mqtt_host, args.mqtt_port)
    mqtt_client.loop_forever()
