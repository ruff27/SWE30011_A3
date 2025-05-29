#!/usr/bin/env python3
"""
SEAAS Discord Bot
Monitors sensor data and provides control interface
"""

import discord
from discord.ext import commands, tasks
import paho.mqtt.client as mqtt
import json
import asyncio
from datetime import datetime
import logging

from dotenv import load_dotenv
import os

load_dotenv()  

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID"))

# MQTT Configuration
MQTT_BROKER = 'test.mosquitto.org'
MQTT_TOPIC_PREFIX = 'seaas'

# Alert Thresholds
TEMP_HIGH = 30
TEMP_LOW = 10
HUMIDITY_HIGH = 80
HUMIDITY_LOW = 20
LIGHT_DARK = 100

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variables
mqtt_client = None
latest_data = {}
alert_cooldown = {}  # Prevent spam

class SEAASBot:
    def __init__(self):
        self.mqtt_client = None
        self.setup_mqtt()
    
    def setup_mqtt(self):
        """Setup MQTT connection"""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.connect(MQTT_BROKER, 1883, 60)
        self.mqtt_client.loop_start()
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connected callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/sensors/#")
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/control/status")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle MQTT messages"""
        global latest_data
        
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            if topic == f"{MQTT_TOPIC_PREFIX}/sensors/all":
                data = json.loads(payload)
                latest_data = data
                asyncio.run_coroutine_threadsafe(
                    check_alerts(data), bot.loop
                )
            
        except Exception as e:
            logger.error(f"MQTT error: {e}")
    
    def publish_command(self, topic, message):
        """Publish command to MQTT"""
        self.mqtt_client.publish(f"{MQTT_TOPIC_PREFIX}/control/{topic}", message)

# Create bot instance
seaas_bot = SEAASBot()

@bot.event
async def on_ready():
    """Bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🟢 SEAAS Bot Online",
            description="Environmental monitoring system is active!",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        await channel.send(embed=embed)
    
    # Start periodic status updates
    status_update.start()

@bot.command(name='status', help='Show current sensor readings')
async def status(ctx):
    """Display current sensor status"""
    if not latest_data:
        await ctx.send("⚠️ No sensor data available yet!")
        return
    
    embed = discord.Embed(
        title="📊 SEAAS Environmental Status",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Add sensor readings
    temp = latest_data.get('temp', 0)
    humidity = latest_data.get('humidity', 0)
    light = latest_data.get('light', 0)
    motion = latest_data.get('motion', 0)
    
    # Temperature field with emoji
    temp_emoji = "🥵" if temp > TEMP_HIGH else "🥶" if temp < TEMP_LOW else "🌡️"
    embed.add_field(
        name=f"{temp_emoji} Temperature",
        value=f"{temp:.1f}°C",
        inline=True
    )
    
    # Humidity field
    humid_emoji = "💧" if humidity > HUMIDITY_HIGH else "🏜️" if humidity < HUMIDITY_LOW else "💦"
    embed.add_field(
        name=f"{humid_emoji} Humidity",
        value=f"{humidity:.1f}%",
        inline=True
    )
    
    # Light field
    light_emoji = "🌞" if light > 500 else "🌙" if light < LIGHT_DARK else "☁️"
    embed.add_field(
        name=f"{light_emoji} Light Level",
        value=f"{light}/1023",
        inline=True
    )
    
    # Motion field
    motion_emoji = "🚶" if motion else "🪑"
    embed.add_field(
        name=f"{motion_emoji} Motion",
        value="Detected" if motion else "None",
        inline=True
    )
    
    # System status
    embed.add_field(
        name="⏰ Last Update",
        value=latest_data.get('timestamp', 'Unknown'),
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='fan', help='Control the fan: !fan on/off/status')
async def fan_control(ctx, action: str = 'status'):
    """Control fan"""
    action = action.lower()
    
    if action in ['on', 'off']:
        seaas_bot.publish_command('fan', action)
        await ctx.send(f"✅ Fan turned **{action.upper()}**")
    elif action == 'status':
        await ctx.send("ℹ️ Use `!status` to see current system state")
    else:
        await ctx.send("❌ Invalid command. Use: `!fan on` or `!fan off`")

@bot.command(name='led', help='Control LED: !led red/green/blue/white/off')
async def led_control(ctx, color: str = 'status'):
    """Control LED color"""
    color = color.lower()
    
    colors = {
        'red': '255,0,0',
        'green': '0,255,0',
        'blue': '0,0,255',
        'white': '255,255,255',
        'purple': '255,0,255',
        'yellow': '255,255,0',
        'cyan': '0,255,255',
        'off': '0,0,0'
    }
    
    if color in colors:
        seaas_bot.publish_command('led', colors[color])
        emoji = "🔴" if color == 'red' else "🟢" if color == 'green' else "🔵" if color == 'blue' else "⚪" if color == 'white' else "🟣" if color == 'purple' else "🟡" if color == 'yellow' else "🟦" if color == 'cyan' else "⚫"
        await ctx.send(f"{emoji} LED set to **{color.upper()}**")
    else:
        await ctx.send("❌ Invalid color. Options: red, green, blue, white, purple, yellow, cyan, off")

@bot.command(name='buzzer', help='Activate buzzer: !buzzer')
async def buzzer_control(ctx):
    """Activate buzzer"""
    seaas_bot.publish_command('buzzer', 'on')
    await ctx.send("🔔 Buzzer activated for 3 seconds!")

@bot.command(name='alert', help='Test alert system')
async def test_alert(ctx):
    """Test the alert system"""
    embed = discord.Embed(
        title="🚨 TEST ALERT",
        description="This is a test of the SEAAS alert system!",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    await ctx.send(embed=embed)

@bot.command(name='help_seaas', help='Show all SEAAS commands')
async def help_seaas(ctx):
    """Custom help command"""
    embed = discord.Embed(
        title="📚 SEAAS Bot Commands",
        description="Environmental monitoring and control system",
        color=discord.Color.green()
    )
    
    commands_list = [
        ("!status", "Show current sensor readings"),
        ("!fan on/off", "Control the fan"),
        ("!led [color]", "Set LED color (red/green/blue/white/off)"),
        ("!buzzer", "Activate buzzer for 3 seconds"),
        ("!alert", "Test the alert system"),
        ("!monitor start/stop", "Start/stop monitoring alerts")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='monitor', help='Start/stop monitoring: !monitor start/stop')
async def monitor_control(ctx, action: str):
    """Control monitoring"""
    action = action.lower()
    
    if action == 'start':
        alert_cooldown.clear()
        await ctx.send("✅ Alert monitoring **STARTED**")
    elif action == 'stop':
        # Set all alerts on cooldown
        for alert_type in ['temp_high', 'temp_low', 'humidity', 'motion']:
            alert_cooldown[alert_type] = datetime.now()
        await ctx.send("⏸️ Alert monitoring **PAUSED**")
    else:
        await ctx.send("❌ Use: `!monitor start` or `!monitor stop`")

async def check_alerts(data):
    """Check for alert conditions"""
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not channel:
        return
    
    current_time = datetime.now()
    alerts = []
    
    # Temperature alerts
    temp = data.get('temp', 0)
    if temp > TEMP_HIGH and should_alert('temp_high', current_time):
        alerts.append({
            'title': '🔥 High Temperature Alert!',
            'desc': f'Temperature is {temp:.1f}°C (threshold: {TEMP_HIGH}°C)',
            'color': discord.Color.red()
        })
    elif temp < TEMP_LOW and should_alert('temp_low', current_time):
        alerts.append({
            'title': '❄️ Low Temperature Alert!',
            'desc': f'Temperature is {temp:.1f}°C (threshold: {TEMP_LOW}°C)',
            'color': discord.Color.blue()
        })
    
    # Humidity alerts
    humidity = data.get('humidity', 0)
    if humidity > HUMIDITY_HIGH and should_alert('humidity_high', current_time):
        alerts.append({
            'title': '💧 High Humidity Alert!',
            'desc': f'Humidity is {humidity:.1f}% (threshold: {HUMIDITY_HIGH}%)',
            'color': discord.Color.blue()
        })
    
    # Security alert
    motion = data.get('motion', 0)
    light = data.get('light', 0)
    if motion and light < LIGHT_DARK and should_alert('motion', current_time):
        alerts.append({
            'title': '🚨 SECURITY ALERT!',
            'desc': f'Motion detected in darkness! (Light level: {light})',
            'color': discord.Color.red()
        })
    
    # Send alerts
    for alert in alerts:
        embed = discord.Embed(
            title=alert['title'],
            description=alert['desc'],
            color=alert['color'],
            timestamp=current_time
        )
        embed.add_field(name="Location", value="Room 101", inline=True)
        embed.add_field(name="Action", value="Check system immediately!", inline=True)
        
        await channel.send(embed=embed)

def should_alert(alert_type, current_time):
    """Check if we should send an alert (cooldown to prevent spam)"""
    if alert_type not in alert_cooldown:
        alert_cooldown[alert_type] = current_time
        return True
    
    # 5 minute cooldown between same alerts
    time_diff = (current_time - alert_cooldown[alert_type]).total_seconds()
    if time_diff > 300:  # 5 minutes
        alert_cooldown[alert_type] = current_time
        return True
    
    return False

@tasks.loop(minutes=30)
async def status_update():
    """Send periodic status updates"""
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if channel and latest_data:
        # Only send if there's something interesting
        temp = latest_data.get('temp', 0)
        if temp > 25 or temp < 15:  # Only if temp is notable
            await status(channel)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `!help_seaas` for available commands.")
    else:
        await ctx.send(f"❌ Error: {str(error)}")

# Run the bot
if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")