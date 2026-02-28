import os
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler

# Legge le variabili d'ambiente
TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("Le variabili d'ambiente BOT_TOKEN e CHAT_ID devono essere impostate!")

bot = Bot(TOKEN)

def start(update: Update, context):
    update.message.reply_text("Ciao! Sono il tuo bot per i sondaggi Forex.")

def sondaggio(update: Update, context):
    survey_url = "https://bitpathforexnews.featurebase.app/survey/<ID-SONDAGGIO>"
    update.message.reply_text(f"Partecipa al sondaggio qui: {survey_url}")

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("sondaggio", sondaggio))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
