import re
import urllib.parse
import os
from functools import wraps  # Necessario per creare il decoratore
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
import random

# --- Caricamento e Gestione Variabili d'Ambiente ---
# Legge gli ID admin da una variabile d'ambiente/secret, separati da virgola
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
AMAZON_AFFILIATE_TAG = os.environ.get("AMAZON_AFFILIATE_TAG", "")
HEADLINE_PHRASES = [
    "🔥 SCONTO DA NON PERDERE!",
    "🚨 PREZZO MINIMO STORICO!",
    "💰 RISPARMIA ORA!",
    "✨ GRANDE AFFARE SU AMAZON!",
    "🎉 OFFERTA ESCLUSIVA!",
    "💥 LEGIONARI, ALL'ATTACCO!",
    "🔍 TROVATO UN SUPER AFFARE!",
    "💸 MAI VISTO UN PREZZO COSÌ!",
    "💥 SCONTO DA NON PERDERE!",
    "🎖️ Vittoria sul Prezzo: MAXI SCONTO!",
    "💥 SCONTO DA NON PERDERE!",  
    "⚔️ L'AFFARE CHE STAVATE ASPETTANDO È ARRIVATO!",
    "⚔️ FINALMENTE IL PREZZO È CROLLATO",    # Aggiunta di una frase casuale
]

if not ADMIN_IDS_STR:
    # Se la variabile non è impostata, il bot risponderà a tutti (utile per test)
    print("ATTENZIONE: La variabile ADMIN_IDS non è impostata. Il bot risponderà a tutti.")
    ADMIN_IDS = []
else:
    try:
        # Converte la stringa di ID in una lista di numeri interi
        ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',')]
        print(f"Bot limitato ai seguenti ID admin: {ADMIN_IDS}")
    except ValueError:
        print("ERRORE: ADMIN_IDS contiene valori non numerici. Il bot non funzionerà correttamente.")
        ADMIN_IDS = []

if not AMAZON_AFFILIATE_TAG:
    print("ATTENZIONE: La variabile AMAZON_AFFILIATE_TAG non è impostata. I link lunghi non saranno affiliati.")

# --- Decoratore per limitare l'accesso agli admin ---
def admin_only(func):
    """
    Decoratore che restringe l'uso di una funzione solo agli admin definiti in ADMIN_IDS.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        # Se la lista ADMIN_IDS è vuota, permette a tutti di usare il bot.
        # Altrimenti, controlla se l'ID utente è nella lista.
        if not ADMIN_IDS or user_id in ADMIN_IDS:
            return await func(update, context, *args, **kwargs)
        else:
            print(f"Accesso negato per l'utente non admin: {user_id}")
            await update.message.reply_text("❌ Non hai il permesso di usare questo bot.")
            return
    return wrapped

# --- Stati della Conversazione ---
PREZZO_INIZIALE, PREZZO_ATTUALE, CONFERMA_INVIO = range(3)
CHANNEL_ID = os.environ.get("CHANNEL_ID") 

# --- Funzioni di Utilità (invariate + nuova) ---
def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

def calculate_discount(current, previous):
    if previous is None or previous <= current or current <= 0:
        return 0
    return round(((previous - current) / previous) * 100)

def apply_affiliate_tag(original_url: str, tag: str) -> str:
    """
    Controlla se il link è short (amzn.to). Se è long (www.amazon.it/...), 
    aggiunge l'affiliate tag, se disponibile.
    """
    # Se è un link short, lo restituisce invariato
    if re.search(r'amzn\.to', original_url, re.IGNORECASE):
        print(f"Link short rilevato, non aggiungo il tag. Link: {original_url}")
        return original_url

    # Se è un link lungo e ho il tag
    if tag:
        # Analizza l'URL
        parsed_url = urllib.parse.urlparse(original_url)
        # Ottiene i parametri di query esistenti
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Sostituisce o aggiunge il parametro tag (tipicamente "tag" o "linkCode" per Amazon)
        query_params['tag'] = [tag]

        # Ricostruisce l'URL con i nuovi parametri
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        final_url = urllib.parse.urlunparse(
            parsed_url._replace(query=new_query, fragment='')
        )
        print(f"Link lungo affiliato. Link originale: {original_url} -> Link affiliato: {final_url}")
        return final_url

    # Se è un link lungo ma il tag non è disponibile, restituisce l'originale
    print(f"Link lungo, ma AMAZON_AFFILIATE_TAG non impostato. Link: {original_url}")
    return original_url

# --- Comandi /start e /help (protetti dal decoratore) ---
@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        r"*Ciao\! Sono il Bot Legione Risparmiatori\.*"
        "\n\n"
        r"Inviami un link Amazon e ti guiderò nella creazione dell'offerta\!",
        parse_mode='MarkdownV2'
    )

@admin_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        r"ℹ️ *Come funziona il bot*:"
        "\n\n"
        r"1\. *Invia un link Amazon* per iniziare\."
        "\n"
        r"2\. Il bot ti chiederà il *prezzo di listino*\."
        "\n"
        r"3\. Successivamente ti chiederà il *prezzo attuale* in offerta\."
        "\n"
        r"4\. Vedrai un'anteprima e potrai *confermare l'invio* al canale\."
        "\n\n"
        r"Usa il comando `/cancel` in qualsiasi momento per interrompere la creazione di un'offerta\.",
        parse_mode='MarkdownV2'
    )

# --- Inizio della Conversazione (protetto dal decoratore) ---
@admin_only
async def amazon_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Gestisce i link Amazon, estrae i dati e inizia la conversazione 
    chiedendo il primo prezzo. Gestisce anche URL di immagini non validi.
    """
    chat_id = update.effective_chat.id
    message_text = update.message.text

    match = re.search(r'(https?://(?:amzn\.to|www\.amazon\.[a-z]{2,3})[^ \r\n]*)', message_text, re.IGNORECASE)
    if not match:
        await context.bot.send_message(chat_id=chat_id, text=r"⚠️ Link non valido\.", parse_mode='MarkdownV2')
        return ConversationHandler.END

    amazon_url = match.group(0)
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    await update.message.reply_text(r"🔎 Analizzo il link, attendi\.\.\.", parse_mode='MarkdownV2')

    # Riattiviamo la tua funzione di scraping.
    # Assicurati che il file `utils.py` con `get_amazon_product_details` sia presente.
    # DEVI IMPORTARE: from utils import get_amazon_product_details
    from utils import get_amazon_product_details 
    product_data = get_amazon_product_details(amazon_url)

    print(f"Dati estratti dal link: {product_data}") # Stampa di debug

    if product_data and product_data.get('title'):

        image_url = product_data.get('image_url')
        if not image_url:
            await update.message.reply_text(
                r"⚠️ Trovato il titolo, ma non sono riuscito a estrarre un'immagine valida\. "
                r"Non posso continuare senza l'immagine\.",
                parse_mode='MarkdownV2'
            )
            return ConversationHandler.END

        # Determina il link da salvare, pulito o originale
        clean_link = product_data.get('clean_product_link')
        original_link = product_data.get('original_link')

        # Se il link è short o se è lungo ma vogliamo affiliarlo
        link_to_affiliate = clean_link or original_link

        # --- LOGICA RICHIESTA: Applica il tag affiliate solo ai link lunghi ---
        final_buy_link = apply_affiliate_tag(link_to_affiliate, AMAZON_AFFILIATE_TAG)
        # --------------------------------------------------------------------

        context.user_data['draft'] = {
            'title': product_data['title'],
            'image_url': image_url,
            'final_buy_link': final_buy_link, # Ora è il link elaborato
        }

        # --- MODIFICA CHIAVE: Gestione dell'errore BadRequest ---
        try:
            # Prova a inviare la foto
            await update.message.reply_photo(
                photo=context.user_data['draft']['image_url'],
                caption=f"*Titolo Estratto:* {escape_markdown_v2(context.user_data['draft']['title'])}",
                parse_mode='MarkdownV2'
            )
        except telegram.error.BadRequest as e:
            # Se fallisce perché l'URL non è un'immagine, invia un messaggio di testo
            if "Wrong type of the web page content" in str(e):
                print(f"Errore: l'URL dell'immagine non è valido. Invio un messaggio di testo alternativo. URL: {image_url}")
                await update.message.reply_text(
                    f"⚠️ *Impossibile caricare l'anteprima dell'immagine*\.\n\n"
                    f"*Titolo Estratto:* {escape_markdown_v2(context.user_data['draft']['title'])}",
                    parse_mode='MarkdownV2'
                )
            else:
                # Se è un altro tipo di errore, lo segnala comunque
                print(f"Si è verificato un BadRequest non gestito: {e}")
                await update.message.reply_text(r"Si è verificato un errore inaspettato con l'anteprima\.")
                return ConversationHandler.END
        # --- FINE MODIFICA ---

        await update.message.reply_text(
            "✅ *Dati recuperati\!* \n\n1️⃣ Inserisci il *prezzo iniziale* \(es: `129.99`\)",
            parse_mode='MarkdownV2'
        )
        return PREZZO_INIZIALE
    else:
        await update.message.reply_text(r"⚠️ Non sono riuscito a trovare i dati del prodotto\. Controlla il link\.", parse_mode='MarkdownV2')
        return ConversationHandler.END

# --- Le funzioni interne alla conversazione non necessitano del decoratore ---
# L'accesso è già stato verificato all'inizio della conversazione.
async def handle_prezzo_iniziale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # (Codice invariato)
    try:
        prezzo_text = update.message.text.replace(',', '.')
        prezzo_precedente = float(prezzo_text)
        context.user_data['draft']['prezzo_precedente'] = prezzo_precedente
        await update.message.reply_text("2️⃣ Ottimo\! Ora inserisci il *prezzo attuale* \(es: `99.99`\)", parse_mode='MarkdownV2')
        return PREZZO_ATTUALE
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Prezzo non valido\. Riprova:", parse_mode='MarkdownV2')
        return PREZZO_INIZIALE

async def handle_prezzo_attuale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # (Codice invariato)
    try:
        prezzo_text = update.message.text.replace(',', '.')
        prezzo_attuale = float(prezzo_text)
        context.user_data['draft']['prezzo_attuale'] = prezzo_attuale
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Prezzo non valido\. Riprova:", parse_mode='MarkdownV2')
        return PREZZO_ATTUALE
    draft = context.user_data['draft']
    caption, reply_markup = build_final_message(draft)
    keyboard = [[InlineKeyboardButton("✅ Invia", callback_data="send"), InlineKeyboardButton("❌ Annulla", callback_data="cancel_post")]]
    confirmation_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("✨ *Anteprima:*", parse_mode='MarkdownV2')
    await context.bot.send_photo(
        chat_id=update.effective_chat.id, photo=draft['image_url'], caption=caption,
        reply_markup=reply_markup, parse_mode='MarkdownV2'
    )
    await update.message.reply_text("Vuoi pubblicarlo?", reply_markup=confirmation_markup)
    return CONFERMA_INVIO

async def handle_conferma_invio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # (Codice invariato)
    query = update.callback_query
    await query.answer()
    if query.data == "send":
        if not CHANNEL_ID:
            await query.edit_message_text(text="❌ *ERRORE:* `CHANNEL_ID` non impostato\.", parse_mode='MarkdownV2')
            return ConversationHandler.END
        draft = context.user_data.get('draft')
        caption, reply_markup = build_final_message(draft)
        try:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=draft['image_url'], caption=caption,
                reply_markup=reply_markup, parse_mode='MarkdownV2'
            )
            await query.edit_message_text(text="✅ Messaggio inviato con successo!")
        except Exception as e:
            await query.edit_message_text(text=f"❌ Errore durante l'invio: {e}")
    elif query.data == "cancel_post":
        await query.edit_message_text(text="❌ Operazione annullata.")
    if 'draft' in context.user_data: del context.user_data['draft']
    return ConversationHandler.END

# --- Funzione per costruire il messaggio  ---
def build_final_message(draft: dict) -> (str, InlineKeyboardMarkup):
    DISCLAIMER_URL = "https://telegra.ph/LEGIONARI-DEL-RISPARMIO-ATTENTI-ALLA-BATTAGLIA-08-27"

    # --- NUOVO TESTO DI INVITO E LINK ---
    # 1. Definisci l'username del tuo canale (assicurati che sia corretto!)
    CHANNEL_USERNAME = "@legionedeirisparmiatori" # <-- MODIFICA QUI CON L'USERNAME REALE (es. @LegionariRisparmiatori)

    # 2. Definisci il messaggio di invito da condividere
    INVITE_TEXT = f"Ciao, ti giro questo canale di OFFERTE ESCLUSIVE, CODICI SCONTO e COUPON: {CHANNEL_USERNAME} \n\n ⚔️ Unisciti anche TU alla Legione dei Risparmiatori⚔️ \n\n Clicca sul link e iscriviti! \n https://t.me/legionedeirisparmiatori \n"

    # 3. Crea il link "share/url" con il messaggio di invito
    # Questo link apre la schermata di condivisione di Telegram con il testo precompilato.
    telegram_invite_share_url = f"https://t.me/share/url?url=&text={urllib.parse.quote_plus(INVITE_TEXT)}"
    # -------------------------------------
    
    intestazioni = random.choice(HEADLINE_PHRASES)
    intestazioni_escaped = escape_markdown_v2(intestazioni)
    title_escaped = escape_markdown_v2(draft['title'])
    prezzo_attuale, prezzo_precedente, final_buy_link = draft['prezzo_attuale'], draft['prezzo_precedente'], draft['final_buy_link']
    prezzo_attuale_escaped, prezzo_precedente_escaped = f"€ {prezzo_attuale:.2f}".replace('.', r'\.'), f"€ {prezzo_precedente:.2f}".replace('.', r'\.')
    sconto = calculate_discount(prezzo_attuale, prezzo_precedente)
    sconto_text = f"🔥 RISPARMI IL {sconto}%!" if sconto > 0 else ""
    prezzo_precedente_line = f"🏷️ *Prezzo Consigliato:* ~{prezzo_precedente_escaped}~\n" if prezzo_precedente > prezzo_attuale else ""
# --- TESTO MESSAGGIO ---    
    caption = (f"*{intestazioni_escaped}\n\n{title_escaped}*\n\n{prezzo_precedente_line}💰 *Prezzo Attuale:* *{prezzo_attuale_escaped}*\n\n*__{escape_markdown_v2(sconto_text)}__*\n\n[DISCLAIMER]({DISCLAIMER_URL})")
    
    whatsapp_text = f"{intestazioni} 🎉 \n\n {draft['title']} \n {sconto_text} PREZZO SCONTATO A € {prezzo_attuale:.2f}\n Acquista qui: {final_buy_link}"
    whatsapp_url, telegram_share_url = f"https://wa.me/?text={urllib.parse.quote_plus(whatsapp_text)}", f"https://t.me/share/url?url={urllib.parse.quote_plus(final_buy_link)}&text={urllib.parse.quote_plus(f'💥 Affare! {draft['title']} a € {prezzo_attuale:.2f}!')}"
    keyboard = [
        [InlineKeyboardButton("🛒 ACQUISTA ORA!", url=final_buy_link)], 
        [InlineKeyboardButton("👥 Invita i tuoi amici", url=telegram_invite_share_url), InlineKeyboardButton("📲 WhatsApp", url=whatsapp_url)]]
    return caption, InlineKeyboardMarkup(keyboard)

# --- Gestore per Annullare (protetto dal decoratore) ---
@admin_only
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if 'draft' in context.user_data: del context.user_data['draft']
    await update.message.reply_text("Operazione annullata.")
    return ConversationHandler.END

# --- Dichiarazione Handler per la conversazione ---
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'(amzn\.to|amazon\.)'), amazon_link_handler)],
    states={
        PREZZO_INIZIALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prezzo_iniziale)],
        PREZZO_ATTUALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prezzo_attuale)],
        CONFERMA_INVIO: [CallbackQueryHandler(handle_conferma_invio)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_user=True
)