import serial
import json
import time
import paho.mqtt.client as mqtt
import logging
from threading import Thread, Lock
import queue

# Configuration
SERIAL_PORT = '/dev/ttyACM0'  # Adjust if needed
SERIAL_BAUD = 9600
MQTT_BROKER = 'test.mosquitto.org'
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = 'seaas/sensors'
MQTT_CONTROL_TOPIC = 'seaas/control'
DEVICE_ID = 'pi_b'

# Control thresholds
TEMP_THRESHOLD_HIGH = 25  # Turn on fan above this
# TEMP_THRESHOLD_LOW = 25   # Turn off fan below this
LIGHT_THRESHOLD = 200     # Below this is considered dark

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActuatorController:
    def __init__(self):
        self.serial_conn = None
        self.mqtt_client = None
        self.command_queue = queue.Queue()
        self.serial_lock = Lock()
        self.current_state = {
            'fan': False,
            'led': {'r': 0, 'g': 255, 'b': 0},  # Green = normal
            'buzzer': False
        }
        self.sensor_data = {
            'temp': 0,
            'humidity': 0,
            'light': 0,
            'motion': 0
        }

    def setup_serial(self):
        """Initialize serial connection to Arduino"""
        try:
            self.serial_conn = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
            time.sleep(2)  # Wait for Arduino reset
            logger.info(f"Serial connection established on {SERIAL_PORT}")

            # Start serial reader thread
            Thread(target=self.serial_reader, daemon=True).start()
            return True
        except Exception as e:
            logger.error(f"Serial connection failed: {e}")
            return False

    def setup_mqtt(self):
        """Initialize MQTT connection"""
        try:
            self.mqtt_client = mqtt.Client(client_id=f"{DEVICE_ID}_{int(time.time())}")
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect

            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT setup failed: {e}")
            return False

    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to sensor data and control commands
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/all")
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/alerts")
            client.subscribe(f"{MQTT_CONTROL_TOPIC}/#")
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')

            if topic == f"{MQTT_TOPIC_PREFIX}/all":
                # Update sensor data
                data = json.loads(payload)
                self.sensor_data.update(data)
                self.process_sensor_data()

            elif topic == f"{MQTT_TOPIC_PREFIX}/alerts":
                # Handle alerts
                alert = json.loads(payload)
                self.handle_alert(alert)

            elif topic.startswith(MQTT_CONTROL_TOPIC):
                # Handle manual control commands
                self.handle_control_command(topic, payload)

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.warning(f"Disconnected from MQTT broker: {rc}")

    def process_sensor_data(self):
        """Process sensor data and determine actuator states"""
        temp = self.sensor_data['temp']
        light = self.sensor_data['light']
        motion = self.sensor_data['motion']

        # Fan control based on temperature
        if temp > TEMP_THRESHOLD_HIGH and not self.current_state['fan']:
            self.control_fan(True)
        else:
            self.control_fan(False)

        # LED status indication
        if temp > TEMP_THRESHOLD_HIGH:
            # Red = hot
            self.control_led(255, 0, 0)
        elif motion and light < LIGHT_THRESHOLD:
            # Blue = motion in dark
            self.control_led(0, 0, 255)
        else:
            # Green = normal
            self.control_led(0, 255, 0)

    def handle_alert(self, alert):
        """Handle alert conditions"""
        alert_type = alert.get('type')

        if alert_type == 'MOTION_IN_DARK':
            # Activate buzzer for security alert
            self.control_buzzer(True)
            self.control_led(255, 0, 255)  # Purple for alert
            logger.warning("Security alert: Motion detected in darkness!")

        elif alert_type == 'HIGH_TEMP':
            # Flash red LED
            for _ in range(3):
                self.control_led(255, 0, 0)
                time.sleep(0.5)
                self.control_led(0, 0, 0)
                time.sleep(0.5)

    def handle_control_command(self, topic, payload):
        """Handle manual control commands via MQTT"""
        command = topic.split('/')[-1]

        if command == 'fan':
            self.control_fan(payload.lower() == 'on')
        elif command == 'led':
            # Expect format: "r,g,b"
            try:
                r, g, b = map(int, payload.split(','))
                self.control_led(r, g, b)
            except:
                logger.error(f"Invalid LED command: {payload}")
        elif command == 'buzzer':
            self.control_buzzer(payload.lower() == 'on')

    def control_fan(self, state):
        """Control fan relay"""
        command = f"FAN:{'ON' if state else 'OFF'}"
        self.send_command(command)
        self.current_state['fan'] = state
        logger.info(f"Fan turned {'ON' if state else 'OFF'}")

    def control_led(self, r, g, b):
        """Control RGB LED"""
        command = f"LED:{r},{g},{b}"
        self.send_command(command)
        self.current_state['led'] = {'r': r, 'g': g, 'b': b}

    def control_buzzer(self, state):
        """Control buzzer"""
        command = f"BUZZER:{'ON' if state else 'OFF'}"
        self.send_command(command)
        self.current_state['buzzer'] = state

    def send_command(self, command):
        """Send command to Arduino via serial"""
        with self.serial_lock:
            if self.serial_conn:
                try:
                    self.serial_conn.write(f"{command}\n".encode())
                    logger.debug(f"Sent command: {command}")
                except Exception as e:
                    logger.error(f"Error sending command: {e}")

    def serial_reader(self):
        """Read responses from Arduino"""
        while True:
            try:
                if self.serial_conn and self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line:
                        logger.debug(f"Arduino response: {line}")

                        # Publish status updates
                        if line.startswith('{'):
                            self.mqtt_client.publish(f"{MQTT_CONTROL_TOPIC}/status", line)

                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error reading serial: {e}")
                time.sleep(1)

    def run(self):
        """Main controller loop"""
        logger.info("Starting Actuator Controller...")

        if not self.setup_serial():
            return

        if not self.setup_mqtt():
            return

        # Set initial LED state
        self.control_led(0, 255, 0)  # Green = ready

        try:
            while True:
                # Request status periodically
                if int(time.time()) % 30 == 0:  # Every 30 seconds
                    self.send_command("STATUS")

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            # Turn off all actuators
            self.control_fan(False)
            self.control_led(0, 0, 0)
            self.control_buzzer(False)

            if self.serial_conn:
                self.serial_conn.close()
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()

if __name__ == "__main__":
    controller = ActuatorController()
    controller.run()