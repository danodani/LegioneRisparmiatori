import os
import psycopg2
import logging

def get_db_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_id BIGINT PRIMARY KEY,
            channel_name TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def get_channels():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT channel_id, channel_name FROM channels")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def add_channel(cid, name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO channels (channel_id, channel_name) VALUES (%s, %s) ON CONFLICT DO NOTHING", (cid, name))
    conn.commit()
    cur.close()
    conn.close()
