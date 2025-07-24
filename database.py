import sqlite3

def init_db():
    """
    Inizializza il database e crea le tabelle se non esistono.
    Questa funzione verrà chiamata all'avvio del bot.
    """
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Esempio di creazione tabella (da adattare alle tue esigenze future)
    # cursor.execute('''
    # CREATE TABLE IF NOT EXISTS users (
    #     id INTEGER PRIMARY KEY,
    #     user_id INTEGER UNIQUE,
    #     username TEXT
    # )
    # ''')
    
    conn.commit()
    conn.close()
    print("Database inizializzato.")

# Qui andranno le altre funzioni per interagire con il DB (INSERT, SELECT, UPDATE, etc.)