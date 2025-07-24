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
logger.info(f"Comando /start ricevuto dall'admin {user_id}")

async def test_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia un messaggio di test al canale (solo per admin)."""
    user_id = update.effective_user.id
    
    # Usa la funzione is_admin per il controllo dei permessi
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per eseguire questo comando.")
        logger.warning(f"Tentativo di accesso non autorizzato al comando /test da parte dell'utente {user_id}")
        return

    channel_id = os.getenv("CHANNEL_ID")
    if not channel_id:
        await update.message.reply_text("Errore: CHANNEL_ID non configurato.")
        logger.error("Errore: CHANNEL_ID non trovato tra le variabili d'ambiente.")
        return

    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text="✅ Messaggio di test inviato correttamente dal bot."
        )
        await update.message.reply_text("Messaggio di test inviato al canale!")
        logger.info(f"Test inviato al canale {channel_id} dall'admin {user_id}")
    except Exception as e:
        await update.message.reply_text(f"Errore durante l'invio del test: {e}")
        logger.error(f"Errore nel comando /test: {e}", exc_info=True) # exc_info=True per stampare il traceback

async def forza_invio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forza l'invio del messaggio programmato (solo per admin)."""
    user_id = update.effective_user.id

    # Usa la funzione is_admin per il controllo dei permessi
    if not is_admin(user_id):
        await update.message.reply_text("❌ Non hai i permessi per eseguire questo comando.")
        logger.warning(f"Tentativo di accesso non autorizzato al comando /forza_invio da parte dell'utente {user_id}")
        return
    
    await update.message.reply_text("Avvio l'invio manuale del messaggio programmato...")
    logger.info(f"Comando /forza_invio ricevuto da admin {user_id}. Avvio invio manuale.")
    
    # La funzione invia_messaggio_programmato deve gestire al suo interno
    # il recupero dell'ID del canale o riceverlo come parametro.
    # In questo caso, la sto chiamando senza argomenti, assumendo che recuperi l'ID al suo interno.
    successo = await invia_messaggio_programmato(context) # La tua funzione scheduler deve accettare 'context'

    if successo:
        await update.message.reply_text("✅ Invio manuale completato con successo!")
        logger.info(f"Invio manuale del messaggio programmato completato da admin {user_id}.")
    else:
        await update.message.reply_text("⚠️ Si è verificato un errore durante l'invio. Controlla i log.")
        logger.error(f"Errore nell'invio manuale del messaggio programmato da admin {user_id}.", exc_info=True)
