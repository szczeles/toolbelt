#!/bin/bash

mosquitto_pub -h osmc -t "tele/temp/$SENSOR_NAME" -m "{\"temperature\": $3, \"humidity\": $4, \"batt_voltage\": $5, \"batt_level\": $6, \"timestamp\": $7}"
