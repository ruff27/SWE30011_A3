import discord
import asyncio
import paho.mqtt.client as mqtt
import os
import json
from dotenv import load_dotenv

# # .env DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1377333528479535116/MTM3NzMzMDU1OTAwNDcwOTAwNA.Gwb0hO.3hUMIoeGlGOPdW461Ii8wJbabml8SixnEOXGxY
# Load .env variables
load_dotenv()

DISCORD_TOKEN = os.getenv(MTM3NzMzMDU1OTAwNDcwOTAwNA.Gwb0hO.3hUMIoeGlGOPdW461Ii8wJbabml8SixnEOXGxY)
ALERT_CHANNEL_ID = int(os.getenv(1377333528479535116))
MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mosquitto.org")
MQTT_TOPIC = "seaas/sensors/alerts"

# Global alert queue
alert_queue = asyncio.Queue()

# Setup Discord Bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"🤖 SEAAS Bot connected as {client.user}")
    client.loop.create_task(process_alerts())

async def process_alerts():
    await client.wait_until_ready()
    channel = client.get_channel(ALERT_CHANNEL_ID)
    
    while True:
        alert = await alert_queue.get()
        await channel.send(alert)

# MQTT Setup
def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        alert_type = payload.get("type", "")
        
        if alert_type == "HIGH_TEMP":
            alert = f"🔥 High Temperature Alert: {payload['value']}°C"
        elif alert_type == "MOTION_IN_DARK":
            alert = f"🚨 Motion Detected in Darkness! Light level: {payload['light']}"
        else:
            alert = f"⚠️ Unknown alert: {json.dumps(payload)}"

        asyncio.run_coroutine_threadsafe(alert_queue.put(alert), client.loop)
        
    except Exception as e:
        print(f"Error handling MQTT message: {e}")

# Start MQTT client in background thread
def start_mqtt():
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()

# Start the system
if __name__ == "__main__":
    print("🚀 Starting SEAAS Discord Bot...")
    start_mqtt()
    client.run(DISCORD_TOKEN)
