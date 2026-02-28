import os
import re
import logging
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask

# Configurazione logging base (visibile nei log di Render)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ================== CONFIGURAZIONE ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    logger.warning("BOT_TOKEN o CHAT_ID non impostati nelle variabili d'ambiente!")

# Sessione persistente per mantenere cookies tra richieste
session = requests.Session()

# Headers realistici (simula Chrome 130+ su Windows 11 – febbraio 2026)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Referer": "https://www.google.com/",
    "DNT": "1",                    # Do Not Track
}

# Imposta gli headers di default sulla sessione
session.headers.update(HEADERS)


def get_ff_json_url():
    """
    Estrae dinamicamente il parametro ?version= dal codice HTML della pagina calendar
    Questo metodo è molto più affidabile rispetto a usare una versione fissa.
    """
    url = "https://www.forexfactory.com/calendar"
    
    try:
        logger.info(f"Recupero version da: {url}")
        response = session.get(url, timeout=12)
        response.raise_for_status()
        
        # Cerca pattern tipico del link JSON con version
        match = re.search(
            r'(?:https?://nfs\.faireconomy\.media/)?ff_calendar_thisweek\.json\?version=([a-f0-9]{32})',
            response.text,
            re.IGNORECASE
        )
        
        if match:
            version = match.group(1)
            full_url = f"https://nfs.faireconomy.media/ff_calendar_thisweek.json?version={version}"
            logger.info(f"Trovata version: {version}")
            return full_url
        
        logger.warning("Version non trovata → fallback URL base")
        return "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    
    except requests.RequestException as e:
        logger.error(f"Errore recupero pagina calendar: {e}")
        return "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def fetch_high_impact_events():
    """Recupera e filtra solo gli eventi High Impact della settimana"""
    url = get_ff_json_url()
    logger.info(f"Fetch eventi da: {url}")
    
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        events = resp.json()  # deve essere una lista di dizionari
    except Exception as e:
        logger.error(f"Errore fetch JSON: {e}")
        return f"❌ Errore nel recupero dati Forex Factory:\n{str(e)[:200]}"

    now = datetime.now(timezone.utc)
    messages = []

    for ev in events:
        if ev.get("impact", "").lower() != "high":
            continue

        try:
            dt_str = ev["date"]
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            
            # Salta eventi già passati
            if dt <= now:
                continue

            # Converti in ora italiana (approssimazione CET/CEST)
            italy_dt = dt + timedelta(hours=6)  # da Eastern Time (-5) → UTC+1
            time_str = italy_dt.strftime("%d/%m/%Y %H:%M")

            msg = (
                f"🔴 **{time_str}** | {ev.get('country', '??')} {ev.get('title', 'Evento sconosciuto')}\n"
                f"Forecast: {ev.get('forecast', '-')}\n"
                f"Previous: {ev.get('previous', '-')}\n"
            )
            messages.append(msg)
        
        except (KeyError, ValueError) as e:
            logger.debug(f"Errore parsing evento: {e} → {ev.get('title')}")
            continue

    if not messages:
        return "🟢 Nessun evento High Impact previsto per questa settimana."

    header = "🗓 **Forex Factory – High Impact Events (settimana corrente)**\n\n"
    content = "\n".join(messages[:12])  # limite ragionevole per Telegram

    if len(content) > 3800:
        content = content[:3800] + "\n\n… (continua con deploy successivo o manualmente)"

    return header + content


def send_telegram_message(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("Impossibile inviare messaggio: token o chat_id mancanti")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logger.info("Messaggio inviato correttamente su Telegram")
            return True
        else:
            logger.error(f"Telegram API errore {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Errore invio messaggio Telegram: {e}")
        return False


# ================== ESECUZIONE AL DEPLOY / RI-AVVIO ==================
logger.info("Avvio Forex Factory High Impact Notifier")
news_text = fetch_high_impact_events()
send_telegram_message(news_text)

send_telegram_message(
    "✅ **Bot Forex Factory avviato su Render**\n"
    "Riceverai le notifiche High Impact al riavvio del servizio.\n"
    f"Ora: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
)


# ================== ROUTES FLASK ==================
@app.route("/")
def home():
    return """
    <h1>Forex Factory High Impact Telegram Notifier</h1>
    <p>Il bot è attivo.<br>
    Le notifiche High Impact vengono inviate al tuo Telegram al momento del deploy / riavvio.</p>
    <p><a href="/send">Prova invio manuale</a></p>
    """


@app.route("/send")
def manual_send():
    msg = fetch_high_impact_events()
    success = send_telegram_message(msg)
    status = "OK ✅" if success else "ERRORE ❌"
    return f"<h2>Invio manuale: {status}</h2><pre>{msg}</pre>"


# ================== AVVIO LOCALE (opzionale) ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
