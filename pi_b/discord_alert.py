import requests
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_alert(message):
    payload = {"content": message}
    headers = {"Content-Type": "application/json"}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers)
    if response.status_code != 204:
        print(f"Failed to send Discord message: {response.status_code} - {response.text}")
