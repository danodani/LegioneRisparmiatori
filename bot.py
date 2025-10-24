import os
import logging
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

# Carica il token del bot dai Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Verifica critica che il token esista
if not TELEGRAM_BOT_TOKEN:
    logger.error("ERRORE: TELEGRAM_BOT_TOKEN non trovato nei Secrets!")
    exit(1)

# Verifica che gli ID admin e l'ID del canale siano stati impostati (opzionale ma consigliato)
if not os.environ.get("ADMIN_IDS"):
    logger.warning("ATTENZIONE: La variabile ADMIN_IDS non è impostata. Il bot risponderà a tutti.")
if not os.environ.get("CHANNEL_ID"):
    logger.warning("ATTENZIONE: La variabile CHANNEL_ID non è impostata. L'invio al canale fallirà.")


def main():
    """Avvia il bot e registra gli handler corretti."""

    # Crea l'applicazione del bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # --- Registrazione degli Handlers ---

    # 1. Aggiungi i comandi di base (/start, /help, /cancel)
    #    Ogni comando viene collegato alla sua funzione corrispondente.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))

    # 2. Aggiungi il ConversationHandler
    #    Questo singolo handler gestisce tutto il flusso di creazione dell'offerta:
    #    ricezione del link, richiesta dei prezzi e conferma.
    application.add_handler(conv_handler)

    # --- Avvio del Bot ---
    logger.info("Bot avviato! In attesa di comandi dagli amministratori...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
