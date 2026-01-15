import time
from db import get_db


def upsert_contact(jid: str, phone: str | None = None, name: str | None = None):
    now = int(time.time() * 1000)
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    INSERT INTO contacts (jid, phone, name, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(jid) DO UPDATE SET
        phone = COALESCE(excluded.phone, phone),
        name = COALESCE(excluded.name, name),
        updated_at = ?
    """, (jid, phone, name, now, now, now))

    db.commit()

    cur.execute("SELECT id FROM contacts WHERE jid = ?", (jid,))
    contact_id = cur.fetchone()[0]

    db.close()
    return contact_id


def insert_message(
    message_id: str,
    jid: str,
    direction: str,
    message_type: str,
    content: str | None,
    media_path: str | None,
    timestamp: int,
    status: str
):
    contact_id = upsert_contact(jid)

    db = get_db()
    cur = db.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO messages (
        message_id, contact_id, direction,
        message_type, content, media_path,
        timestamp, status, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message_id,
        contact_id,
        direction,
        message_type,
        content,
        media_path,
        timestamp,
        status,
        int(time.time() * 1000)
    ))

    db.commit()
    db.close()


def update_message_status(message_id: str, status: str):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
    UPDATE messages SET status = ?
    WHERE message_id = ?
    """, (status, message_id))

    db.commit()
    db.close()

def update_contact_presence(
    jid: str,
    phone: str | None,
    name: str | None,
    is_online: bool
):
    now = int(time.time() * 1000)

    db = get_db()
    cur = db.cursor()

    cur.execute("""
    INSERT INTO contacts (
        jid, phone, name,
        last_seen_at, is_online,
        created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(jid) DO UPDATE SET
        phone = COALESCE(excluded.phone, phone),
        name = COALESCE(excluded.name, name),
        last_seen_at = excluded.last_seen_at,
        is_online = excluded.is_online,
        updated_at = ?
    """, (
        jid,
        phone,
        name,
        now,
        1 if is_online else 0,
        now,
        now,
        now
    ))

    db.commit()
    db.close()
