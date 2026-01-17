import sqlite3
import json
import os

CONFIG_FILE = "db_config.json"

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

DB_PATH = config.get("sqlite_path", "data/whatsapp.db")
POSTGRES_DSN = (
    os.getenv("POSTGRES_DSN")
    or config.get("postgres_dsn")
    or None
)

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

try:
    import psycopg2  # type: ignore
except ImportError:
    psycopg2 = None  # type: ignore


def has_postgres():
    return bool(POSTGRES_DSN and psycopg2 is not None)


def get_db():
    return sqlite3.connect(DB_PATH)


def get_pg_db():
    if not has_postgres():
        return None
    return psycopg2.connect(POSTGRES_DSN)  # type: ignore[arg-type]


def init_db():
    db = get_db()
    cur = db.cursor()

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

    try:
        cur.execute("ALTER TABLE login_sessions ADD COLUMN created_at_str TEXT")
    except Exception:
        pass

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

    try:
        cur.execute("ALTER TABLE contacts ADD COLUMN last_seen_at_str TEXT")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE contacts ADD COLUMN created_at_str TEXT")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE contacts ADD COLUMN updated_at_str TEXT")
    except Exception:
        pass

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

    try:
        cur.execute("ALTER TABLE messages ADD COLUMN timestamp_str TEXT")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE messages ADD COLUMN created_at_str TEXT")
    except Exception:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS message_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        comment TEXT,
        created_at INTEGER,
        FOREIGN KEY(message_id) REFERENCES messages(id)
    )
    """)

    try:
        cur.execute("ALTER TABLE message_comments ADD COLUMN created_at_str TEXT")
    except Exception:
        pass

    db.commit()
    db.close()

    if not has_postgres():
        return

    try:
        pg = get_pg_db()
        if pg is None:
            return

        cur_pg = pg.cursor()

        cur_pg.execute("""
        CREATE TABLE IF NOT EXISTS login_sessions (
            id SERIAL PRIMARY KEY,
            jid TEXT,
            lid TEXT,
            phone TEXT,
            status TEXT,
            created_at BIGINT,
            created_at_str TEXT
        )
        """)

        cur_pg.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            jid TEXT UNIQUE,
            phone TEXT,
            name TEXT,
            profile_pic TEXT,
            last_seen_at BIGINT,
            is_online BOOLEAN,
            created_at BIGINT,
            updated_at BIGINT
        )
        """)

        cur_pg.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            message_id TEXT UNIQUE,
            contact_id INTEGER REFERENCES contacts(id),
            direction TEXT,
            message_type TEXT,
            content TEXT,
            media_path TEXT,
            timestamp BIGINT,
            status TEXT,
            created_at BIGINT,
            timestamp_str TEXT,
            created_at_str TEXT
        )
        """)

        cur_pg.execute("""
        CREATE TABLE IF NOT EXISTS message_comments (
            id SERIAL PRIMARY KEY,
            message_id INTEGER REFERENCES messages(id),
            comment TEXT,
            created_at BIGINT,
            created_at_str TEXT
        )
        """)

        cur_pg.execute(
            "ALTER TABLE login_sessions ADD COLUMN IF NOT EXISTS created_at_str TEXT"
        )

        cur_pg.execute(
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS last_seen_at_str TEXT"
        )

        cur_pg.execute(
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS created_at_str TEXT"
        )

        cur_pg.execute(
            "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS updated_at_str TEXT"
        )

        cur_pg.execute(
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS timestamp_str TEXT"
        )

        cur_pg.execute(
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS created_at_str TEXT"
        )

        cur_pg.execute(
            "ALTER TABLE message_comments ADD COLUMN IF NOT EXISTS created_at_str TEXT"
        )

        pg.commit()
        pg.close()
    except Exception as e:
        print("Postgres init failed:", e)
