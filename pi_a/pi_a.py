import serial
import json
import time
import paho.mqtt.client as mqtt
import logging
from datetime import datetime
# Import custom Discord alert function
from discord_alert import send_discord_alert

# Configuration
SERIAL_PORT = '/dev/ttyUSB0'  # Adjust if needed (could be /dev/ttyACM0)
SERIAL_BAUD = 9600
MQTT_BROKER = 'test.mosquitto.org'  # Public broker for testing
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = 'seaas/sensors'
DEVICE_ID = 'pi_a'

# Thingsboard configuration (optional)
THINGSBOARD_HOST = 'demo.thingsboard.io'  # Replace with your instance
THINGSBOARD_TOKEN = 'YOUR_DEVICE_TOKEN'   # Replace with actual token

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorGateway:
    def __init__(self):
        self.serial_conn = None
        self.mqtt_client = None
        self.tb_client = None  # Thingsboard client
        self.last_data = {}
        
    def setup_serial(self):
        """Initialize serial connection to Arduino"""
        try:
            self.serial_conn = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
            time.sleep(2)  # Wait for Arduino reset
            logger.info(f"Serial connection established on {SERIAL_PORT}")
            return True
        except Exception as e:
            logger.error(f"Serial connection failed: {e}")
            return False
    
    def setup_mqtt(self):
        """Initialize MQTT connection"""
        try:
            # Setup local MQTT broker connection
            self.mqtt_client = mqtt.Client(client_id=f"{DEVICE_ID}_{int(time.time())}")
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
            
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            
            # Setup Thingsboard connection (optional)
            self.tb_client = mqtt.Client()
            self.tb_client.username_pw_set(THINGSBOARD_TOKEN)
            try:
                self.tb_client.connect(THINGSBOARD_HOST, 1883, 60)
                self.tb_client.loop_start()
                logger.info("Connected to Thingsboard")
            except:
                logger.warning("Thingsboard connection failed - continuing without it")
            
            return True
        except Exception as e:
            logger.error(f"MQTT setup failed: {e}")
            return False
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to command topics
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/commands/#")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.warning(f"Disconnected from MQTT broker: {rc}")
    
    def read_sensor_data(self):
        """Read data from Arduino"""
        if self.serial_conn and self.serial_conn.in_waiting > 0:
            try:
                line = self.serial_conn.readline().decode('utf-8').strip()
                
                if line.startswith('{') and line.endswith('}'):
                    # Parse JSON data
                    data = json.loads(line)
                    self.last_data = data
                    self.process_sensor_data(data)
                elif line == "SENSOR_NODE_READY":
                    logger.info("Arduino sensor node is ready")
                elif line.startswith("ERROR:"):
                    logger.error(f"Arduino error: {line}")
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {line}")
            except Exception as e:
                logger.error(f"Error reading serial data: {e}")
    
    def process_sensor_data(self, data):
        """Process and publish sensor data"""
        timestamp = datetime.now().isoformat()
        
        # Add timestamp to data
        data['timestamp'] = timestamp
        
        # Publish to MQTT topics
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/temperature", data['temp'])
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/humidity", data['humidity'])
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/light", data['light'])
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/motion", data['motion'])
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/all", json.dumps(data))
        
        # Publish to Thingsboard
        if self.tb_client:
            tb_telemetry = {
                'temperature': data['temp'],
                'humidity': data['humidity'],
                'light': data['light'],
                'motion': data['motion']
            }
            self.tb_client.publish('v1/devices/me/telemetry', json.dumps(tb_telemetry))
        
        logger.info(f"Published sensor data: Temp={data['temp']}°C, Humidity={data['humidity']}%, Light={data['light']}, Motion={data['motion']}")
        
        # Check for alerts
        self.check_alerts(data)
    
    def check_alerts(self, data):
        """Check sensor data for alert conditions"""
        alerts = []
        
        # Temperature alerts
        if data['temp'] > 30:
            alerts.append({"type": "HIGH_TEMP", "value": data['temp']})
            send_discord_alert(f"🔥 High temperature detected: {data['temp']}°C")
        elif data['temp'] < 10:
            alerts.append({"type": "LOW_TEMP", "value": data['temp']})
            send_discord_alert(f"❄️ Low temperature detected: {data['temp']}°C")
        
        # Motion in darkness alert
        if data['motion'] == 1 and data['light'] < 100:
            alerts.append({"type": "MOTION_IN_DARK", "light": data['light']})
            send_discord_alert(f"🚨 Motion detected in darkness! Light level: {data['light']}")
        
        # Publish alerts
        for alert in alerts:
            self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/alerts", json.dumps(alert))
            logger.warning(f"Alert: {alert}")
    
    def run(self):
        """Main gateway loop"""
        logger.info("Starting Sensor Gateway...")
        
        if not self.setup_serial():
            return
        
        if not self.setup_mqtt():
            return
        
        try:
            while True:
                self.read_sensor_data()
                time.sleep(0.1)  # Small delay to prevent CPU overload
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            if self.serial_conn:
                self.serial_conn.close()
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            if self.tb_client:
                self.tb_client.loop_stop()
                self.tb_client.disconnect()

if __name__ == "__main__":
    gateway = SensorGateway()
    gateway.run()