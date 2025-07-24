import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Abilita il logging per avere output dettagliato
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Funzioni Handler di Esempio (per verificare che gli handler funzionino) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia un messaggio di benvenuto quando il comando /start è ricevuto."""
    await update.message.reply_text('Ciao! Sono il tuo bot. Sono attivo e in ascolto.')




# --- Funzione principale del bot ---

def main() -> None:
    """Avvia il bot in modalità polling."""
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        logger.error("Errore: La variabile d'ambiente BOT_TOKEN non è impostata.")
        exit(1) # Termina il bot se il token non è presente

    # Costruisci l'applicazione
    application = Application.builder().token(BOT_TOKEN).build()

    # Registra gli handler di esempio
    # Se questi funzionano, sai che la base per aggiungere le tue funzionalità è solida.
    application.add_handler(CommandHandler("start", start))

    # Avvia il bot
    logger.info("Bot avviato e in ascolto in modalità polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
