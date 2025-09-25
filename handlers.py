import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from urllib.parse import quote_plus
from utils import get_amazon_product_details, AFFILIATE_TAG 


# --- Funzioni di utilità per i calcoli ---


def calculate_discount(current, previous):
    """Calcola la percentuale di sconto, restituisce 0 se non applicabile."""
    if previous is None or previous <= current or current <= 0:
        return 0
    return round(((previous - current) / previous) * 100)


# --- Handlers dei Comandi di Base ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il comando /start."""
    await update.message.reply_text(
        "Ciao! Sono il Bot Legione Risparmiatori. Inviami un link Amazon e ti fornirò tutti i dettagli sull'offerta!"
    )


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce il comando /help."""
    await update.message.reply_text(
        "Funzionalità:\n"
        "- Invia un link Amazon per ricevere i dettagli dell'offerta, i prezzi e un link affiliato da condividere.\n"
        "- I comandi di base sono /start e /help.")


# --- Handler per Link Amazon (Nuova Funzionalità) ---


async def amazon_link_handler(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce i messaggi che contengono un link Amazon per lo scraping e la formattazione."""

    chat_id = update.effective_chat.id
    message_text = update.message.text

    # --- NUOVA LOGICA DI ESTRAZIONE ---
    # Usiamo re.search per trovare il primo link Amazon nel testo
    match = re.search(r'(https?://(?:amzn\.to|www\.amazon\.[a-z]{2,3})[^ \r\n]*)', message_text, re.IGNORECASE)

    if not match:
        # Se non trova l'URL (non dovrebbe succedere se il filtro funziona)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Sembra mancare un link Amazon valido.")
        return

    amazon_url = match.group(0) # Prende l'URL completo trovato
    # --- FINE NUOVA LOGICA ---

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    await update.message.reply_text("🔎 Analizzo l'offerta Amazon, attendi...")

    # 1. Recupera i dati del prodotto da utils.py
    product_data = get_amazon_product_details(amazon_url)

    if not product_data or not product_data.get("title"):
        await context.bot.send_message(
            chat_id=chat_id,
            text=
            "⚠️ Non sono riuscito a trovare i dettagli del prodotto o il link non è valido."
        )
        return

    # Calcola lo sconto
    sconto_percent = calculate_discount(product_data["current_price"],
                                        product_data["previous_price"])

    # Formattazione del testo
    prezzo_attuale = f"€ {product_data['current_price']:.2f}"

    if sconto_percent > 0:
        prezzo_precedente = f"**Prezzo Precedente:** ~~€ {product_data['previous_price']:.2f}~~\n"
        sconto_line = f" ({sconto_percent}%)"
    else:
        prezzo_precedente = ""
        sconto_line = ""

    caption_text = (f"🎁 **{product_data['title']}**\n\n"
                    f"🏷️ **Prezzo Attuale:** {prezzo_attuale}{sconto_line}\n"
                    f"📈 {prezzo_precedente}"
                    f"\n👉 Per l'offerta clicca qui")

    # 2. Crea i bottoni inline

    # Testo precompilato per la condivisione
    share_text = quote_plus(
        f"💥 Affare Trovato! {product_data['title']} a {prezzo_attuale}! Controlla subito: {product_data['product_link']}"
    )
    # Link di condivisione Telegram (che apre l'interfaccia di condivisione)
    telegram_share_url = f"https://t.me/share/url?url={quote_plus(product_data['product_link'])}&text={share_text}"

    # Bottoni
    button_buy = InlineKeyboardButton(
        text="🛒 Acquista subito",
        url=product_data["product_link"]  # Link affiliato
    )
    button_share = InlineKeyboardButton(text="📲 Condividi Offerta",
                                        url=telegram_share_url)

    keyboard = InlineKeyboardMarkup([[button_buy], [button_share]])

    # 3. Invia la foto e la caption (messaggio)
    try:
        await context.bot.send_photo(chat_id=chat_id,
                                     photo=product_data["image_url"],
                                     caption=caption_text,
                                     parse_mode='Markdown',
                                     reply_markup=keyboard)
    except Exception as e:
        # Fallback se la foto non è valida o manca
        await context.bot.send_message(
            chat_id=chat_id,
            text=
            f"Ecco l'offerta:\n{caption_text}\n\n⚠️ Impossibile caricare l'immagine.",
            parse_mode='Markdown',
            reply_markup=keyboard)


# --- Dichiarazione degli Handlers per bot.py ---

start_handler = CommandHandler("start", start)
help_handler = CommandHandler("help", help_command)
amazon_link_message_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND & filters.Regex(r'(amzn\.to|amazon\.)'),
    amazon_link_handler)
