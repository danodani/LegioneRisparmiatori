import re
import os
import logging
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from utils import scrape_amazon_product, create_final_message
from database import get_all_channels, add_channel

# Stati della conversazione
PREZZO_INIZIALE, PREZZO_ATTUALE, SCEGLI_CANALE = range(3)

ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x]

def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Accesso negato.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Legione Risparmiatori Online!\nInvia un link Amazon per iniziare.")

@admin_only
async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: `/setchannel -100xxx NomeCanale`", parse_mode='Markdown')
        return
    try:
        cid = int(context.args[0])
        name = " ".join(context.args[1:])
        add_channel(cid, name)
        await update.message.reply_text(f"✅ Canale {name} salvato!")
    except:
        await update.message.reply_text("❌ ID Canale non valido.")

async def amazon_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = update.message.text
    await update.message.reply_text("🔍 Recupero dati da Amazon...")
    product_data = scrape_amazon_product(url)
    
    if not product_data:
        await update.message.reply_text("❌ Impossibile recuperare il prodotto. Riprova.")
        return ConversationHandler.END

    context.user_data['draft'] = product_data
    await update.message.reply_text("✅ Dati recuperati! Inserisci il *prezzo iniziale* (es: 120.50):", parse_mode='Markdown')
    return PREZZO_INIZIALE

async def handle_prezzo_iniziale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        prezzo = float(update.message.text.replace(',', '.'))
        context.user_data['draft']['old_price'] = prezzo
        await update.message.reply_text("Ottimo! Ora inserisci il *prezzo attuale* (scontato):", parse_mode='Markdown')
        return PREZZO_ATTUALE
    except:
        await update.message.reply_text("❌ Inserisci un numero valido.")
        return PREZZO_INIZIALE

async def handle_prezzo_attuale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        prezzo = float(update.message.text.replace(',', '.'))
        context.user_data['draft']['new_price'] = prezzo
        
        channels = get_all_channels()
        if not channels:
            await update.message.reply_text("⚠️ Nessun canale configurato. Usa /setchannel.")
            return ConversationHandler.END

        keyboard = [[InlineKeyboardButton(f"Invia su {c[1]}", callback_data=f"pub_{c[0]}")] for c in channels]
        keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="cancel_pub")])
        
        await update.message.reply_text("📦 Offerta pronta! Scegli il canale di destinazione:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SCEGLI_CANALE
    except:
        await update.message.reply_text("❌ Inserisci un numero valido.")
        return PREZZO_ATTUALE

async def publish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_pub":
        await query.edit_message_text("Operazione annullata.")
        return ConversationHandler.END

    channel_id = int(query.data.replace("pub_", ""))
    draft = context.user_data.get('draft')
    
    caption, reply_markup = create_final_message(draft)
    
    try:
        await context.bot.send_photo(chat_id=channel_id, photo=draft['image_url'], caption=caption, reply_markup=reply_markup, parse_mode='Markdown')
        await query.edit_message_text("✅ Offerta pubblicata con successo!")
    except Exception as e:
        await query.edit_message_text(f"❌ Errore durante l'invio: {e}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'(amazon\.|amzn\.)'), amazon_link_handler)],
    states={
        PREZZO_INIZIALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prezzo_iniziale)],
        PREZZO_ATTUALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prezzo_attuale)],
        SCEGLI_CANALE: [CallbackQueryHandler(publish_callback, pattern="^pub_"), CallbackQueryHandler(cancel, pattern="cancel_pub")]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
