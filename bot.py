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
    """Avvia il bot in modalità polling per Replit."""
    # Carica le variabili d'ambiente
    load_dotenv()
    
    # Prendi il token del bot
    token = os.getenv("BOT_TOKEN")
    if not token:
        logging.critical("BOT_TOKEN non trovato! Assicurati di aver impostato la variabile d'ambiente BOT_TOKEN.")
        return
        
    # Inizializza il database
    init_db()

    # Crea l'applicazione del bot
    application = ApplicationBuilder().token(token).build()

    # Aggiunge gli handler per i comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", test_channel))
    application.add_handler(CommandHandler("forza_invio", forza_invio))

    # --- Configurazione per Replit (modalità polling) ---
    logging.info("Avvio del bot in modalità Polling")
    logging.info("Bot avviato con successo! Premi Ctrl+C per fermare.")
    
    try:
        application.run_polling(allowed_updates=['message', 'callback_query'])
    except KeyboardInterrupt:
        logging.info("Bot fermato dall'utente.")
    except Exception as e:
        logging.error(f"Errore durante l'esecuzione del bot: {e}", exc_info=True)


if __name__ == '__main__':
    main()