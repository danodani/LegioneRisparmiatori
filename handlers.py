import os
import logging
from telegram import Update
from telegram.ext import ContextTypes

# Importa la funzione dallo scheduler
from scheduler import invia_messaggio_programmato

# --- Configurazione Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Carica gli ID degli amministratori per i controlli di sicurezza ---
# Inizializza una lista vuota per gli ID degli amministratori
ADMIN_IDS = []

admin_ids_str = os.getenv("ADMIN_IDS") # Il nome della variabile d'ambiente su Render
if admin_ids_str:
    try:
        # Divide la stringa per virgola e converte ogni parte in un intero
        # .strip() rimuove eventuali spazi bianchi attorno agli ID
        ADMIN_IDS = [int(aid.strip()) for aid in admin_ids_str.split(',')]
        logger.info(f"Caricati ID amministratori: {ADMIN_IDS}")
    except ValueError:
        logger.error(f"Errore nella conversione degli ADMIN_IDS: '{admin_ids_str}'. Assicurati che siano numeri interi separati da virgole.")
        ADMIN_IDS = [] # In caso di errore, la lista rimane vuota per sicurezza
else:
    logger.warning("Variabile d'ambiente ADMIN_IDS non impostata. Nessun amministratore configurato.")


# --- Funzione di Utilità per Verificare l'Amministratore ---
def is_admin(user_id: int) -> bool:
    """Controlla se l'ID dell'utente è nella lista degli amministratori."""
    return user_id in ADMIN_IDS

# inizializzo i comandi 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Risponde al comando /start con un messaggio di benvenuto."""
    user = update.effective_user
    await update.message.reply_html(
        f"Ciao {user.mention_html()}! 👋\n\n"
        "Benvenuto nel bot de La Legione dei Risparmiatori. "
        "Il bot è attualmente in funzione"
    )

async def test_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia un messaggio di test al canale (solo per admin)."""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Non hai i permessi per eseguire questo comando.")
        return

    channel_id = os.getenv("CHANNEL_ID")
    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text="✅ Messaggio di test inviato correttamente dal bot."
        )
        await update.message.reply_text("Messaggio di test inviato al canale!")
        logging.info(f"Test inviato al canale {channel_id} dall'admin {user_id}")
    except Exception as e:
        await update.message.reply_text(f"Errore durante l'invio del test: {e}")
        logging.error(f"Errore nel comando /test: {e}")

async def forza_invio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forza l'invio del messaggio programmato (solo per admin)."""
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Non hai i permessi per eseguire questo comando.")
        return
    
    await update.message.reply_text("Avvio l'invio manuale del messaggio programmato...")
    
    successo = await invia_messaggio_programmato(context)

    if successo:
        await update.message.reply_text("✅ Invio manuale completato con successo!")
    else:
        await update.message.reply_text("⚠️ Si è verificato un errore durante l'invio. Controlla i log.")
