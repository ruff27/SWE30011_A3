# discord_alert.py
import requests

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1377526074904150107/yTBKYWDt2PI2YTqzAW_K_iNHIN0FiMeIfY73w49OtlfdiwBkbKOujGGyagYfyRfom0Y_"

def send_discord_alert(message):
    payload = {"content": message}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print("✅ Alert sent to Discord")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
