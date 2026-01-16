import os
import psycopg2
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    """Stabilisce la connessione al database Postgres (Neon)."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL non impostata!")
        return None
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Errore connessione DB: {e}")
        return None

def init_db():
    """
    Inizializza il database e crea le tabelle se non esistono.
    """
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    
    # Esempio tabella Canali (per quando implementerai il multi-canale)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id BIGINT PRIMARY KEY,
            channel_name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("Database Postgres inizializzato.")
