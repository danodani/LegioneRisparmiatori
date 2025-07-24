import os
import logging
from telegram import Update
from telegram.ext import ContextTypes

# Importa la funzione dallo scheduler
from scheduler import invia_messaggio_programmato

# Carica l'ID dell'amministratore per i controlli di sicurezza
try:
    ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
except (ValueError, TypeError):
    ADMIN_USER_ID = None # Se l'ID non è un numero valido o non è impostato

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
