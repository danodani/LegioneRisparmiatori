import os
import logging
from dotenv import load_dotenv

from telegram.ext import ApplicationBuilder, CommandHandler

# Importa i gestori dei comandi (nessuna modifica qui)
from handlers import start, test_channel, forza_invio
from database import init_db

# Configura il logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

def main() -> None:
    """Avvia il bot in modalità webhook per il deploy su Render."""
    # Carica le variabili d'ambiente (utile per lo sviluppo locale)
    load_dotenv()
    
    # Prendi il token del bot
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.critical("BOT_TOKEN non trovato!")
        return
        
    # Inizializza il database
    init_db()

    # Crea l'applicazione del bot
    application = ApplicationBuilder().token(token).build()

    # Aggiunge gli handler per i comandi (nessuna modifica qui)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test_channel))
    application.add_handler(CommandHandler("forza_invio", forza_invio))

    # --- Configurazione Webhook per Render ---
    # Render imposta la porta dinamicamente tramite la variabile PORT
    port = int(os.getenv("PORT", 8443))
    # Render fornisce l'URL pubblico del servizio tramite RENDER_EXTERNAL_URL
    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    
    if webhook_url:
        # Avvia il bot in modalità webhook
        logging.info(f"Avvio in modalità Webhook su porta {port}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,  # Usa il token come parte "segreta" dell'URL
            webhook_url=f"{webhook_url}/{token}"
        )
    else:
        # Se non siamo su Render, avvia in modalità polling per test locali
        logging.info("Avvio in modalità Polling per sviluppo locale")
        application.run_polling()


if __name__ == '__main__':
    main()
