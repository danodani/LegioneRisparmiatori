import os
import sqlite3
import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Abilita il logging per avere output dettagliato
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# -- Funzioni di utilità per il database --
DATABASE_NAME = 'risparmi.db'

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regole (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            parola_chiave TEXT NOT NULL,
            percentuale REAL NOT NULL,
            UNIQUE(user_id, categoria, parola_chiave)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transazioni (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            descrizione TEXT NOT NULL,
            importo REAL NOT NULL,
            risparmio_calcolato REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def aggiungi_regola_db(user_id, categoria, parola_chiave, percentuale):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO regole (user_id, categoria, parola_chiave, percentuale) VALUES (?, ?, ?, ?)",
                       (user_id, categoria, parola_chiave, percentuale))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Regola già esistente
    finally:
        conn.close()

def rimuovi_regola_db(user_id, categoria, parola_chiave):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM regole WHERE user_id = ? AND categoria = ? AND parola_chiave = ?",
                   (user_id, categoria, parola_chiave))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_regole_utente(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT categoria, parola_chiave, percentuale FROM regole WHERE user_id = ?", (user_id,))
    regole = cursor.fetchall()
    conn.close()
    return regole

def salva_transazione_db(user_id, data, descrizione, importo, risparmio_calcolato):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transazioni (user_id, data, descrizione, importo, risparmio_calcolato) VALUES (?, ?, ?, ?, ?)",
                   (user_id, data, descrizione, importo, risparmio_calcolato))
    conn.commit()
    conn.close()

def get_statistiche_utente(user_id, periodo):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    end_date = datetime.now()
    if periodo == 'settimana':
        start_date = end_date - timedelta(days=7)
    elif periodo == 'mese':
        start_date = end_date - timedelta(days=30)
    elif periodo == 'anno':
        start_date = end_date - timedelta(days=365)
    else: # Tutti i tempi
        start_date = datetime.min

    start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("SELECT SUM(risparmio_calcolato), SUM(importo) FROM transazioni WHERE user_id = ? AND data >= ?",
                   (user_id, start_date_str))
    risultato = cursor.fetchone()
    conn.close()
    return risultato if risultato else (0, 0)

# -- Funzioni Handler --

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Ciao! Sono il Bot Legione Risparmiatori. Invia le tue spese e ti aiuterò a risparmiare!\n'
        'Usa /help per vedere tutti i comandi.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Ecco i comandi disponibili:\n\n'
        '/risparmio - Avvia la funzionalità di risparmio automatico (non implementato completamente in questo bot, ma funge da base)\n'
        '/aggiungi_regola <categoria> <parola_chiave> <percentuale> - Aggiunge una regola di risparmio. Esempio: /aggiungi_regola Trasporti Benzina 5\n'
        '/rimuovi_regola <categoria> <parola_chiave> - Rimuove una regola. Esempio: /rimuovi_regola Trasporti Benzina\n'
        '/elenca_regole - Mostra tutte le tue regole di risparmio.\n'
        '/statistiche [settimana|mese|anno|totale] - Mostra le tue statistiche di risparmio. Esempio: /statistiche mese\n'
        'Invia una spesa in formato "descrizione importo", es: "Caffè 2.50" per registrare la spesa e calcolare il risparmio.'
    )

async def aggiungi_regola(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Sintassi: /aggiungi_regola <categoria> <parola_chiave> <percentuale>")
        return

    user_id = update.effective_user.id
    categoria = args[0].lower()
    parola_chiave = args[1].lower()
    try:
        percentuale = float(args[2])
        if not (0 <= percentuale <= 100):
            await update.message.reply_text("La percentuale deve essere tra 0 e 100.")
            return
    except ValueError:
        await update.message.reply_text("La percentuale deve essere un numero valido.")
        return

    if aggiungi_regola_db(user_id, categoria, parola_chiave, percentuale):
        await update.message.reply_text(
            f"Regola aggiunta: Se la spesa contiene '{parola_chiave}' nella categoria '{categoria}', risparmia il {percentuale}%."
        )
    else:
        await update.message.reply_text(
            f"Errore: La regola per '{parola_chiave}' nella categoria '{categoria}' esiste già o c'è stato un problema."
        )

async def rimuovi_regola(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Sintassi: /rimuovi_regola <categoria> <parola_chiave>")
        return

    user_id = update.effective_user.id
    categoria = args[0].lower()
    parola_chiave = args[1].lower()

    if rimuovi_regola_db(user_id, categoria, parola_chiave):
        await update.message.reply_text(f"Regola per '{parola_chiave}' nella categoria '{categoria}' rimossa.")
    else:
        await update.message.reply_text("Regola non trovata o c'è stato un problema.")

async def elenca_regole(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    regole = get_regole_utente(user_id)

    if not regole:
        await update.message.reply_text("Non hai ancora impostato alcuna regola di risparmio.")
        return

    response = "Le tue regole di risparmio:\n\n"
    for categoria, parola_chiave, percentuale in regole:
        response += f"- Categoria: {categoria.capitalize()}, Parola chiave: '{parola_chiave}', Percentuale: {percentuale}%\n"
    await update.message.reply_text(response)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Tenta di parsare il messaggio come "descrizione importo"
    parts = text.rsplit(' ', 1) # Divide una volta sola dall'ultima occorrenza di spazio

    if len(parts) < 2:
        await update.message.reply_text("Formato non riconosciuto. Invia la spesa come 'descrizione importo', es: 'Caffè 2.50'.")
        return

    descrizione = parts[0].strip()
    try:
        importo = float(parts[1].replace(',', '.')) # Gestisce anche la virgola decimale
        if importo <= 0:
            await update.message.reply_text("L'importo deve essere un numero positivo.")
            return
    except ValueError:
        await update.message.reply_text("Importo non valido. Assicurati che sia un numero, es: 'Caffè 2.50'.")
        return

    regole = get_regole_utente(user_id)
    risparmio_calcolato = 0.0
    regola_applicata = None

    for categoria_regola, parola_chiave, percentuale in regole:
        if parola_chiave.lower() in descrizione.lower():
            risparmio_calcolato = importo * (percentuale / 100)
            regola_applicata = f"Regola: '{parola_chiave}' ({percentuale}%)"
            break # Applica la prima regola che corrisponde

    salva_transazione_db(user_id, current_date, descrizione, importo, risparmio_calcolato)

    response_message = f"Spesa registrata: '{descrizione}', Importo: €{importo:.2f}."
    if risparmio_calcolato > 0:
        response_message += f"\nHai risparmiato: €{risparmio_calcolato:.2f} grazie a {regola_applicata}!"
    else:
        response_message += "\nNessuna regola di risparmio applicata a questa spesa."

    await update.message.reply_text(response_message)


async def statistiche(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    periodo = 'totale'
    if context.args:
        periodo = context.args[0].lower()
        if periodo not in ['settimana', 'mese', 'anno', 'totale']:
            await update.message.reply_text("Periodo non valido. Usa 'settimana', 'mese', 'anno' o 'totale'.")
            return

    totale_risparmio, totale_speso = get_statistiche_utente(user_id, periodo)

    if totale_speso == 0:
        await update.message.reply_text(f"Non hai ancora registrato spese per il periodo '{periodo}'.")
    else:
        await update.message.reply_text(
            f"Statistiche per il periodo '{periodo}':\n"
            f"Spesa totale: €{totale_speso:.2f}\n"
            f"Risparmio totale calcolato: €{totale_risparmio:.2f}"
        )

# -- Funzione principale del bot --

def main() -> None:
    init_db() # Inizializza il database all'avvio

    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        logger.error("Errore: La variabile d'ambiente BOT_TOKEN non è impostata.")
        exit(1) # Termina il bot se il token non è presente

    # Costruisci l'applicazione
    application = Application.builder().token(BOT_TOKEN).build()

    # Registra gli handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("risparmio", help_command)) # Puoi decidere di rimuoverlo o implementarlo
    application.add_handler(CommandHandler("aggiungi_regola", aggiungi_regola))
    application.add_handler(CommandHandler("rimuovi_regola", rimuovi_regola))
    application.add_handler(CommandHandler("elenca_regole", elenca_regole))
    application.add_handler(CommandHandler("statistiche", statistiche))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Avvia il bot
    logger.info("Bot avviato e in ascolto...")
    application.run_polling(allowed_updates=Update.ALL_TYPES) # Consigliato specificare allowed_updates per performance

if __name__ == "__main__":
    main()
