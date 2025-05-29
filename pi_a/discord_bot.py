import os
import json
import paho.mqtt.client as mqtt
import discord
import asyncio
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID"))
MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mosquitto.org")
MQTT_TOPIC = "seaas/sensors/alerts"

# Global alert queue
alert_queue = asyncio.Queue()

# Discord bot setup
intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Discord bot connected as {client.user}")
    client.loop.create_task(process_alerts())

async def process_alerts():
    await client.wait_until_ready()
    channel = client.get_channel(ALERT_CHANNEL_ID)
    while True:
        alert = await alert_queue.get()
        await channel.send(embed=alert)

# MQTT setup
def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        embed = discord.Embed(
            title="🚨 Alert from SEAAS",
            description=json.dumps(payload, indent=2),
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        asyncio.run_coroutine_threadsafe(alert_queue.put(embed), client_loop)
    except Exception as e:
        print(f"❌ Failed to process MQTT message: {e}")

# MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

# Run Discord bot
client_loop = asyncio.get_event_loop()
client.run(DISCORD_TOKEN)
