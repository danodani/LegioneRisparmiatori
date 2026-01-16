import os
import logging
from telegram.ext import Application, CommandHandler
from telegram import Update
from dotenv import load_dotenv

# Carica le variabili dal file .env (fondamentale per il test locale)
load_dotenv()

# Importa le funzioni e il conversation handler dal tuo file handlers.py
from handlers import start, help_command, conv_handler, cancel
from database import init_db

# Configurazione del logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Carica il token del bot dai Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    logger.error("ERRORE: TELEGRAM_BOT_TOKEN non trovato nei Secrets!")
    exit(1)

def main():
    """Avvia il bot e registra gli handler corretti."""
    # Inizializza il database SQLite
    init_db()

    # Crea l'applicazione del bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Registrazione degli Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))

    # Gestisce tutto il flusso: link -> prezzo1 -> prezzo2 -> conferma
    application.add_handler(conv_handler)

    # --- Avvio del Bot ---
    logger.info("🚀 Bot avviato! In attesa di comandi dagli amministratori...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()