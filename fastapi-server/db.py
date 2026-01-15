import sqlite3
import json
import os

CONFIG_FILE = "db_config.json"

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

DB_PATH = config.get("sqlite_path", "data/whatsapp.db")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    db = get_db()
    cur = db.cursor()

    # Login / device info
    cur.execute("""
    CREATE TABLE IF NOT EXISTS login_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jid TEXT,
        lid TEXT,
        phone TEXT,
        status TEXT,
        created_at INTEGER
    )
    """)

    # Contacts table (LID ↔ phone mapping)
    cur.execute("""
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jid TEXT UNIQUE,
    phone TEXT,
    name TEXT,
    profile_pic TEXT,
    last_seen_at INTEGER,
    is_online INTEGER,
    created_at INTEGER,
    updated_at INTEGER
)
""")


    # Messages table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE,
        contact_id INTEGER,
        direction TEXT,
        message_type TEXT,
        content TEXT,
        media_path TEXT,
        timestamp INTEGER,
        status TEXT,
        created_at INTEGER,
        FOREIGN KEY(contact_id) REFERENCES contacts(id)
    )
    """)

    # Comments / reactions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS message_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        comment TEXT,
        created_at INTEGER,
        FOREIGN KEY(message_id) REFERENCES messages(id)
    )
    """)

    db.commit()
    db.close()
