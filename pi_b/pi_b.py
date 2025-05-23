# pi_b.py
import serial
import paho.mqtt.client as mqtt

# Serial config for Arduino #2
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=2)

# Thresholds
TEMP_THRESHOLD = 30.0
LIGHT_THRESHOLD = 400
MOTION_REQUIRED = 1.0

def parse_sensor_data(payload):
    try:
        parts = payload.split(',')
        data = {}
        for part in parts:
            k, v = part.split(':')
            data[k.strip()] = float(v.strip())
        return data
    except:
        return {}

def on_message(client, userdata, msg):
    print("Received:", msg.payload.decode())
    data = parse_sensor_data(msg.payload.decode())

    if data:
        # Fan + LED logic
        if data["TEMP"] > TEMP_THRESHOLD:
            ser.write(b"FAN:ON\n")
            ser.write(b"LED:1,0,0\n")  # Red
        else:
            ser.write(b"FAN:OFF\n")
            ser.write(b"LED:0,1,0\n")  # Green

        # Buzzer logic
        if data["LIGHT"] < LIGHT_THRESHOLD and data["MOTION"] == MOTION_REQUIRED:
            ser.write(b"BUZZER:ON\n")
        else:
            ser.write(b"BUZZER:OFF\n")

client = mqtt.Client("PiB_Subscriber")
client.on_message = on_message
client.connect("test.mosquitto.org", 1883, 60)
client.subscribe("group6/sensors")

print("Listening on MQTT topic: group6/sensors")
client.loop_forever()
