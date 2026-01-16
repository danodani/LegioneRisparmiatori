import os
import psycopg2
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    """Stabilisce la connessione al database Postgres su Neon."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL non impostata nelle variabili d'ambiente!")
        return None
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Errore connessione DB: {e}")
        return None

def init_db():
    """Crea la tabella per i canali se non esiste."""
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                channel_id BIGINT PRIMARY KEY,
                channel_name TEXT
            )
        ''')
        conn.commit()
        cursor.close()
        logger.info("Database inizializzato con successo.")
    except Exception as e:
        logger.error(f"Errore init_db: {e}")
    finally:
        conn.close()

def add_channel(channel_id, name):
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO channels (channel_id, channel_name) VALUES (%s, %s) ON CONFLICT (channel_id) DO UPDATE SET channel_name = EXCLUDED.channel_name", (channel_id, name))
        conn.commit()
        cursor.close()
    finally:
        conn.close()

def get_all_channels():
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, channel_name FROM channels")
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        conn.close()
