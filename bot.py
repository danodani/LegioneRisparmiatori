import os
import logging
import threading
from flask import Flask
from telegram.ext import Application, CommandHandler
from telegram import Update

# Importa le funzioni e il conversation handler dal tuo file handlers.py
from handlers import start, help_command, conv_handler, cancel

# Configurazione del logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE FLASK PER RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running!", 200

def run_flask():
    # Render assegna la porta nella variabile d'ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
# ---------------------------------------

# Carica il token del bot
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    logger.error("ERRORE: TELEGRAM_BOT_TOKEN non trovato nelle variabili d'ambiente!")
    exit(1)

def main():
    """Avvia il bot e registra gli handler."""
    
    # 1. Avvia il server Flask in un thread separato (per Render)
    threading.Thread(target=run_flask, daemon=True).start()

    # 2. Crea l'applicazione del bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Registrazione degli Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(conv_handler)

    # --- Avvio del Bot ---
    logger.info("Bot avviato su Render! In attesa di comandi...")
    
    # Usa polling (va bene anche su Render se usi il trucco di Flask)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
