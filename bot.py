import os
import re
import hashlib
import asyncio
import sqlite3
import uuid
import feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import aiohttp
from dotenv import load_dotenv
import sys
print("Python version:", sys.version)
print("Contenuto della directory:", os.listdir("."))

# === CARICA CONFIG ===
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "legionedeiris-21")
DB_FILE = "offerte.db"

# === DATABASE ===
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS offerte (
    id TEXT PRIMARY KEY,
    titolo TEXT,
    url TEXT,
    prezzo_attuale TEXT,
    prezzo_vecchio TEXT,
    sconto TEXT,
    timestamp DATETIME
)
""")
conn.commit()

# === UTILITY ===
def gia_inviata(id_offerta: str) -> bool:
    tre_giorni_fa = datetime.utcnow() - timedelta(days=3)
    c.execute("DELETE FROM offerte WHERE timestamp < ?", (tre_giorni_fa,))
    conn.commit()
    c.execute("SELECT 1 FROM offerte WHERE id = ?", (id_offerta,))
    return c.fetchone() is not None

def salva_offerta(id_offerta: str, titolo: str, url: str, prezzo_attuale: str, prezzo_vecchio: str, sconto: str):
    c.execute("""
        INSERT OR REPLACE INTO offerte (id, titolo, url, prezzo_attuale, prezzo_vecchio, sconto, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (id_offerta, titolo, url, prezzo_attuale, prezzo_vecchio, sconto, datetime.utcnow()))
    conn.commit()

async def crea_link_affiliazione(asin: str, titolo: str = "") -> str:
    if titolo:
        titolo_pulito = re.sub(r'[^\w\s-]', '', titolo).strip()
        titolo_pulito = re.sub(r'[-\s]+', '-', titolo_pulito)[:50]
        return f"https://www.amazon.it/{titolo_pulito}/dp/{asin}?tag={AFFILIATE_TAG}&linkCode=as2&ascsubtag=telegram_bot"
    else:
        return f"https://www.amazon.it/dp/{asin}?tag={AFFILIATE_TAG}&linkCode=as2&ascsubtag=telegram_bot"

async def estrai_img_da_camel(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                img = soup.select_one("#product-image img")
                return img["src"] if img else None
    except Exception as e:
        print(f"Errore estrazione immagine: {e}")
        return None

# === OFFERTA ===
async def fetch_offerta_da_feed():
    feed_url = "https://it.camelcamelcamel.com/top_drops/feed"
    feed = feedparser.parse(feed_url)

    for entry in feed.entries:
        try:
            titolo = entry.title
            camel_url = entry.link
            asin_match = re.search(r'/product/([A-Z0-9]{10})', camel_url)
            if not asin_match:
                continue
            asin = asin_match.group(1)
            amazon_link = await crea_link_affiliazione(asin, titolo)
            id_offerta = hashlib.md5(amazon_link.encode()).hexdigest()
            if gia_inviata(id_offerta):
                continue
            prezzo_match = re.search(r'down (.*?) \((.*?)\) to (.*?) from (.*?)$', titolo)
            if not prezzo_match:
                continue
            sconto, diff, prezzo_attuale, prezzo_vecchio = prezzo_match.groups()
            img = await estrai_img_da_camel(camel_url)
            return {
                "id": id_offerta,
                "titolo": titolo,
                "url": amazon_link,
                "prezzo_attuale": prezzo_attuale,
                "prezzo_vecchio": prezzo_vecchio,
                "sconto": sconto,
                "img": img
            }
        except Exception as e:
            print(f"Errore parsing feed: {e}")
            continue
    return None

async def invia_offerta():
    offerta = await fetch_offerta_da_feed()
    if not offerta:
        print("Nessuna nuova offerta da inviare.")
        return None
    salva_offerta(offerta["id"], offerta["titolo"], offerta["url"], offerta["prezzo_attuale"], offerta["prezzo_vecchio"], offerta["sconto"])
    testo = f"""
🔥 <b>OFFERTA LAMPO</b> 🔥

📦 <b>{offerta['titolo']}</b>

💰 <b>PREZZO: {offerta['prezzo_attuale']}€</b>
🏷️ <s>Prezzo precedente: {offerta['prezzo_vecchio']}€</s>
🎯 <b>SCONTO: {offerta['sconto']}</b>

🛒 <a href=\"{offerta['url']}\">➤ ACQUISTA SUBITO</a>

📱 <a href=\"https://api.whatsapp.com/send?text=🔥 OFFERTA AMAZON 🔥%0A{offerta['titolo']}%0A💰 {offerta['prezzo_attuale']}€ invece di {offerta['prezzo_vecchio']}€%0A🎯 {offerta['sconto']} di sconto%0A%0A🛒 {offerta['url']}\">Condividi su WhatsApp</a>

⚡ <i>Offerta a tempo limitato - Affrettati!</i>
"""
    if offerta['img']:
        await tg_app.bot.send_photo(chat_id=CHANNEL_ID, photo=offerta['img'], caption=testo, parse_mode="HTML")
    else:
        await tg_app.bot.send_message(chat_id=CHANNEL_ID, text=testo, parse_mode="HTML")
    return offerta

async def invia_riepilogo():
    oggi = datetime.utcnow().date()
    c.execute("SELECT titolo, url FROM offerte WHERE date(timestamp) = ?", (oggi,))
    risultati = c.fetchall()
    if risultati:
        testo = "<b>🕘 Riepilogo offerte del giorno:</b>\n\n"
        for titolo, url in risultati:
            testo += f"<b>{titolo[:50]}...</b>\n👉 <a href=\"{url}\">Vedi offerta</a>\n\n"
        await tg_app.bot.send_message(chat_id=CHANNEL_ID, text=testo, parse_mode="HTML")

# === COMANDI TELEGRAM ===
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot attivo e funzionante!")

async def prova(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="🟢 Questo è un messaggio di prova dal bot!")
        await update.message.reply_text("✅ Messaggio di prova inviato nel canale!")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {str(e)}")

async def test_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        asin_test = "B08N5WRWNW"
        titolo_test = "Echo Dot Amazon"
        link = await crea_link_affiliazione(asin_test, titolo_test)
        await update.message.reply_text(
            f"🔗 <b>Link di test generato:</b>\n\n"
            f"📦 Prodotto: {titolo_test}\n"
            f"🔗 Link: <code>{link}</code>\n\n"
            f"✅ Link formattato correttamente per Amazon Associates",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Errore nella generazione del link: {str(e)}")

async def forza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        offerta = await invia_offerta()
        if offerta:
            await update.message.reply_text("✅ Offerta inviata con successo!")
        else:
            await update.message.reply_text("ℹ️ Nessuna nuova offerta disponibile al momento")
    except Exception as e:
        await update.message.reply_text(f"❌ Errore: {str(e)}")

# === SCHEDULER ===
async def setup_scheduler(application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(invia_offerta, "interval", minutes=45, timezone="Europe/Rome")
    scheduler.add_job(invia_riepilogo, "cron", hour=22, minute=0, timezone="Europe/Rome")
    scheduler.start()
    return scheduler

# === AVVIO BOT ===
tg_app = None

def main():
    global tg_app
    tg_app = ApplicationBuilder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("test", test))
    tg_app.add_handler(CommandHandler("prova", prova))
    tg_app.add_handler(CommandHandler("forza", forza))
    tg_app.add_handler(CommandHandler("testlink", test_link))

    async def post_init(application):
        application.scheduler = await setup_scheduler(application)

    tg_app.post_init = post_init

    tg_app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
