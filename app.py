import os
import requests
import logging
from telegram import Bot
import pytz

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise RuntimeError("BOT_TOKEN e CHAT_ID devono essere impostati")

FOREX_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
bot = Bot(token=TOKEN)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
sent_events = set()

# ================= FUNZIONI =================
def fetch_forex_news():
    try:
        resp = requests.get(FOREX_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Errore fetch: {e}")
        return []

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")
        logging.info("Messaggio inviato")
    except Exception as e:
        logging.error(f"Errore Telegram: {e}")

def check_news(initial=False):
    news = fetch_forex_news()
    for event in news:
        if event.get("impact") != "High":
            continue
        event_id = event.get("id")
        if event_id in sent_events:
            continue
        msg = f"📊 *HIGH IMPACT NEWS*\n💱 {event.get('currency')}\n📰 {event.get('title')}\n⏰ {event.get('date')}"
        if initial:
            msg = "📌 *NEWS HIGH IMPACT QUESTA SETTIMANA*\n" + msg
        send_telegram_message(msg)
        sent_events.add(event_id)

# ================= HANDLER LAMBDA =================
def handler(event, context):
    # Questa funzione viene chiamata da Lambda
    check_news()
    return {
        "statusCode": 200,
        "body": "Bot eseguito!"
    }
