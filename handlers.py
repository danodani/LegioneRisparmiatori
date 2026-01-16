import re
import urllib.parse
import os
import random
import asyncio
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ConversationHandler, 
    CallbackQueryHandler
)
import telegram.error 

# --- Configurazione ---
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
AMAZON_AFFILIATE_TAG = os.environ.get("AMAZON_AFFILIATE_TAG", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID") 

HEADLINE_PHRASES = [
    "🔥 SCONTO DA NON PERDERE!", "🚨 PREZZO MINIMO STORICO!", "💰 RISPARMIA ORA!",
    "✨ GRANDE AFFARE SU AMAZON!", "🎉 OFFERTA ESCLUSIVA!", "💥 LEGIONARI, ALL'ATTACCO!",
    "🔍 TROVATO UN SUPER AFFARE!", "💸 MAI VISTO UN PREZZO COSÌ!",
    "🎖️ Vittoria sul Prezzo: MAXI SCONTO!", "⚔️ L'AFFARE CHE STAVATE ASPETTANDO È ARRIVATO!",
    "⚔️ FINALMENTE IL PREZZO È CROLLATO"
]

# Parsing ADMIN_IDS
if not ADMIN_IDS_STR:
    ADMIN_IDS = []
else:
    try:
        ADMIN_IDS = [int(aid.strip()) for aid in ADMIN_IDS_STR.split(',')]
    except ValueError:
        ADMIN_IDS = []

# --- Decoratore ---
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not ADMIN_IDS or user_id in ADMIN_IDS:
            return await func(update, context, *args, **kwargs)
        else:
            print(f"[LOG] Accesso negato per l'utente: {user_id}")
            await update.message.reply_text("❌ Non hai il permesso di usare questo bot.")
            return
    return wrapped

# --- Stati della Conversazione ---
PREZZO_INIZIALE, PREZZO_ATTUALE, CONFERMA_INVIO = range(3)

# --- Funzioni di Utilità ---
def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

def calculate_discount(current, previous):
    if previous is None or previous <= current or current <= 0: return 0
    return round(((previous - current) / previous) * 100)

def apply_affiliate_tag(original_url: str, tag: str) -> str:
    if not original_url:
        return ""
    if re.search(r'amzn\.to', original_url, re.IGNORECASE): 
        return original_url
    if tag:
        parsed_url = urllib.parse.urlparse(original_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query_params['tag'] = [tag]
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        # CORREZIONE: urlunparse invece di unparse
        return urllib.parse.urlunparse(parsed_url._replace(query=new_query, fragment=''))
    return original_url

# --- Handlers ---
@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"[LOG] Comando /start ricevuto da {update.effective_user.id}")
    await update.message.reply_text(r"*Ciao\! Inviami un link Amazon per iniziare\.Pezzo di MERDA!*", parse_mode='MarkdownV2')

@admin_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(r"ℹ️ Invia un link Amazon, poi inserisci i prezzi quando richiesti\.", parse_mode='MarkdownV2')

@admin_only
async def amazon_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = update.message.text
    print(f"\n--- [LOG] Ricevuto messaggio con link: {message_text[:50]}... ---")
    
    # Cerchiamo il link nel messaggio
    match = re.search(r'(https?://(?:amzn\.[a-z]{2,3}|www\.amazon\.[a-z]{2,3})[^ \r\n]*)', message_text, re.IGNORECASE)
    
    if not match:
        print("[LOG] Errore: Nessun link Amazon valido trovato.")
        await update.message.reply_text(r"⚠️ Link non riconosciuto\.", parse_mode='MarkdownV2')
        return ConversationHandler.END

    # DEFINIAMO LA VARIABILE QUI (così i tentativi sotto la vedono)
    amazon_url = match.group(0)
    print(f"[LOG] Link estratto: {amazon_url}")
    
    await update.message.reply_text(r"🔎 Analizzo il link\.\.\.", parse_mode='MarkdownV2')

    from utils import get_amazon_product_details 
    
    product_data = None
    tentativi = 3
    
    # CICLO DI TENTATIVI (Retries)
    for i in range(tentativi):
        print(f"[LOG] Tentativo scraping {i+1} di {tentativi}...")
        try:
            # Passiamo l'url estratto sopra
            product_data = get_amazon_product_details(amazon_url)
            if product_data and product_data.get('title'):
                print(f"[LOG] Successo al tentativo {i+1}!")
                break 
        except Exception as e:
            print(f"[LOG] Errore tecnico al tentativo {i+1}: {e}")
        
        if i < tentativi - 1:
            print("[LOG] Amazon ha bloccato o ASIN non trovato. Riprovo tra 2 secondi...")
            await asyncio.sleep(2) 

    if product_data and product_data.get('title'):
        # Salvataggio dati e invio anteprima (come prima)
        image_url = product_data.get('image_url')
        final_link = apply_affiliate_tag(product_data.get('clean_product_link') or product_data.get('original_link'), AMAZON_AFFILIATE_TAG)
        
        context.user_data['draft'] = {
            'title': product_data['title'],
            'image_url': image_url,
            'final_buy_link': final_link
        }

        if image_url:
            await update.message.reply_photo(photo=image_url, caption=f"✅ {escape_markdown_v2(product_data['title'])}", parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(f"✅ {escape_markdown_v2(product_data['title'])}", parse_mode='MarkdownV2')

        await update.message.reply_text("1️⃣ Inserisci il prezzo iniziale (es: 129.99):")
        return PREZZO_INIZIALE
    else:
        print("[LOG] Scraping fallito definitivamente dopo 3 tentativi.")
        await update.message.reply_text(r"❌ Amazon ha bloccato la richiesta dopo vari tentativi\. Riprova tra un po'\.", parse_mode='MarkdownV2')
        return ConversationHandler.END

async def handle_prezzo_iniziale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text
    print(f"[DEBUG] Ricevuto prezzo iniziale: {txt}")
    try:
        # Pulizia del testo e conversione
        val = float(txt.replace('€', '').replace(',', '.').strip())
        context.user_data['draft']['prezzo_precedente'] = val
        
        print(f"[DEBUG] Prezzo salvato: {val}. Chiedo prezzo scontato.")
        await update.message.reply_text(r"2️⃣ Ottimo\! Ora inserisci il *prezzo attuale* \(scontato\):", parse_mode='MarkdownV2')
        return PREZZO_ATTUALE
    except ValueError:
        print(f"[DEBUG] Errore conversione per: {txt}")
        await update.message.reply_text(r"❌ Inserisci un numero valido \(es: 49.90\):", parse_mode='MarkdownV2')
        return PREZZO_INIZIALE

async def handle_prezzo_attuale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = update.message.text
    print(f"[DEBUG] Ricevuto prezzo attuale: {txt}")
    try:
        val = float(txt.replace('€', '').replace(',', '.').strip())
        context.user_data['draft']['prezzo_attuale'] = val
        
        print(f"[DEBUG] Prezzo attuale salvato: {val}. Genero anteprima...")
        
        draft = context.user_data['draft']
        caption, reply_markup = build_final_message(draft)
        
        # Invio anteprima
        await update.message.reply_text(r"✨ *Anteprima del post:*", parse_mode='MarkdownV2')
        await context.bot.send_photo(
            chat_id=update.effective_chat.id, 
            photo=draft['image_url'], 
            caption=caption,
            reply_markup=reply_markup, 
            parse_mode='MarkdownV2'
        )
        
        confirm_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Invia al Canale", callback_data="send"),
            InlineKeyboardButton("❌ Annulla", callback_data="cancel_post")
        ]])
        await update.message.reply_text("Ti piace? Clicca per pubblicare o annullare:", reply_markup=confirm_kb)
        return CONFERMA_INVIO
        
    except ValueError:
        print(f"[DEBUG] Errore conversione prezzo attuale: {txt}")
        await update.message.reply_text(r"❌ Inserisci un numero valido per il prezzo attuale:", parse_mode='MarkdownV2')
        return PREZZO_ATTUALE

async def handle_conferma_invio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    print(f"[LOG] Callback ricevuto: {query.data}")
    if query.data == "send":
        if not CHANNEL_ID:
            print("[LOG] Errore: CHANNEL_ID non configurato.")
            await query.edit_message_text("❌ CHANNEL_ID non impostato.")
            return ConversationHandler.END
        
        draft = context.user_data.get('draft')
        caption, reply_markup = build_final_message(draft)
        try:
            print(f"[LOG] Tentativo di invio al canale {CHANNEL_ID}...")
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=draft['image_url'], caption=caption, reply_markup=reply_markup, parse_mode='MarkdownV2')
            print("[LOG] Invio completato con successo!")
            await query.edit_message_text("✅ Pubblicato con successo!")
        except Exception as e:
            print(f"[LOG] Errore durante l'invio al canale: {e}")
            await query.edit_message_text(f"❌ Errore invio: {e}")
    else:
        print("[LOG] Post annullato dall'utente.")
        await query.edit_message_text("❌ Operazione annullata.")
    
    return ConversationHandler.END

def build_final_message(draft: dict) -> (str, InlineKeyboardMarkup):
    CHANNEL_USERNAME = "@legionedeirisparmiatori"
    INVITE_TEXT = f"Entra nella Legione delle offerte! ⚔️ {CHANNEL_USERNAME}\nhttps://t.me/legionedeirisparmiatori"
    
    intestazione = random.choice(HEADLINE_PHRASES)
    title = escape_markdown_v2(draft['title'])
    p_att = draft['prezzo_attuale']
    p_pre = draft['prezzo_precedente']
    
    p_att_esc = f"€ {p_att:.2f}".replace('.', r'\.')
    p_pre_esc = f"€ {p_pre:.2f}".replace('.', r'\.')
    sconto = calculate_discount(p_att, p_pre)
    
    sconto_text = f"🔥 RISPARMI IL {sconto}%!" if sconto > 0 else ""
    prezzo_line = f"🏷️ *Prezzo Consigliato:* ~{p_pre_esc}~\n" if p_pre > p_att else ""
    
    caption = (f"*{escape_markdown_v2(intestazione)}*\n\n"
               f"*{title}*\n\n"
               f"{prezzo_line}💰 *Prezzo Attuale:* *{p_att_esc}*\n\n"
               f"*__{escape_markdown_v2(sconto_text)}__*\n\n"
               f"[DISCLAIMER](https://telegra.ph/LEGIONARI-DEL-RISPARMIO-ATTENTI-ALLA-BATTAGLIA-08-27)")
    
    share_msg = f"💥 Affare! {draft['title']} a € {p_att:.2f}!"
    telegram_share_url = f"https://t.me/share/url?url={urllib.parse.quote_plus(draft['final_buy_link'])}&text={urllib.parse.quote_plus(share_msg)}"
    invite_url = f"https://t.me/share/url?url=&text={urllib.parse.quote_plus(INVITE_TEXT)}"

    keyboard = [
        [InlineKeyboardButton("🛒 ACQUISTA ORA!", url=draft['final_buy_link'])],
        [InlineKeyboardButton("👥 Invita Amici", url=invite_url),
         InlineKeyboardButton("📲 WhatsApp", url=f"https://wa.me/?text={urllib.parse.quote_plus(share_msg + ' ' + draft['final_buy_link'])}")]
    ]
    return caption, InlineKeyboardMarkup(keyboard)

@admin_only
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(f"[LOG] Conversazione annullata da {update.effective_user.id}")
    context.user_data.clear()
    await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r'(amzn\.|amazon\.)'), 
            amazon_link_handler
        )
    ],
    states={
        PREZZO_INIZIALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prezzo_iniziale)],
        PREZZO_ATTUALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prezzo_attuale)],
        CONFERMA_INVIO: [CallbackQueryHandler(handle_conferma_invio)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_user=True
)