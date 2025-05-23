# pi_a.py
import serial
import time
import paho.mqtt.client as mqtt
import json

# Serial setup (check your port!)
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=2)

# MQTT (Edge → Pi B)
edge_client = mqtt.Client("PiA_Edge_Publisher")
edge_client.connect("test.mosquitto.org", 1883, 60)

# MQTT (Cloud → ThingsBoard)
cloud_client = mqtt.Client("PiA_ThingsBoard_Publisher")
cloud_client.username_pw_set("YOUR_THINGSBOARD_ACCESS_TOKEN")  # Replace with actual token
cloud_client.connect("demo.thingsboard.io", 1883, 60)

print("Pi A ready – publishing to test.mosquitto.org and ThingsBoard")

while True:
    try:
        line = ser.readline().decode('utf-8').strip()

        if line.startswith("TEMP:"):
            print("Raw Data:", line)

            # Parse sensor values
            parts = line.split(',')
            data = {}
            for part in parts:
                k, v = part.split(':')
                data[k.strip()] = float(v.strip())

            # Publish to edge topic
            edge_client.publish("group6/sensors", line)

            # Publish to ThingsBoard cloud
            payload = {
                "temperature": data.get("TEMP", 0),
                "humidity": data.get("HUMIDITY", 0),
                "light": data.get("LIGHT", 0),
                "motion": int(data.get("MOTION", 0))
            }
            cloud_client.publish("v1/devices/me/telemetry", json.dumps(payload))
        
        time.sleep(2)
    except Exception as e:
        print("Error:", e)
        time.sleep(2)
