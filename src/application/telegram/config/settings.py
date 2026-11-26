import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in .env file")

NGROK_TOKEN = os.getenv("NGROK_TOKEN")
if not NGROK_TOKEN:
    raise ValueError("NGROK_TOKEN not found in .env file")

SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", 5000))
WEBHOOK_PATH = "/telegram"