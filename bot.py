import os
import logging
from telegram.ext import Application, ApplicationBuilder
from telegram import Update
from handlers import start_handler, help_handler, amazon_link_message_handler
    # Assicurati di importare tutti gli handler, inclusi quelli Amazon!

    # Configurazione logging
logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    # Imposta il livello di logging più alto per la libreria per non inondare il log
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

    # --- Replit Secrets Loading ---
    # Replit carica automaticamente le variabili d'ambiente (Secrets)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

    # Verifica critica del Token
if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN non trovato. Assicurati di averlo impostato nei Secrets di Replit.")
        exit(1)


def main():
        """Avvia il bot e registra gli handlers."""

        # Usiamo ApplicationBuilder per creare l'applicazione del bot
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # --- Registrazione degli Handlers ---

        # Comandi di base
        application.add_handler(start_handler)
        application.add_handler(help_handler)

        # Nuovo Handler per i link Amazon
        application.add_handler(amazon_link_message_handler)

        # Se hai altri handler (es. scheduler, database, ecc.), aggiungili qui
        # application.add_handler(altro_handler)

        # --- Avvio del Bot (Polling) ---
        logger.info("Bot avviato! In attesa di messaggi...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
        main()