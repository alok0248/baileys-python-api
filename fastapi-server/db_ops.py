import time
from db import get_db, get_pg_db, has_postgres


def format_timestamp(ts_ms: int | None) -> str | None:
    if not ts_ms:
        return None
    try:
        seconds = ts_ms / 1000.0
        t = time.localtime(seconds)
        return time.strftime("%d/%m/%Y %H:%M:%S", t)
    except Exception:
        return None


def extract_phone_from_jid(jid: str) -> str | None:
    try:
        local_part, domain = jid.split("@", 1)
    except Exception:
        return None

    if domain != "s.whatsapp.net":
        return None

    if not local_part:
        return None

    if local_part.startswith("+"):
        digits = local_part[1:]
        if digits.isdigit():
            return local_part
        return None

    if local_part.isdigit():
        return local_part

    return None


def upsert_contact(jid: str, phone: str | None = None, name: str | None = None):
    if phone is None:
        phone = extract_phone_from_jid(jid)

    if has_postgres():
        try:
            pg = get_pg_db()
            if pg is None:
                return None

            cur_pg = pg.cursor()
            cur_pg.execute(
                "SELECT id, phone, name FROM contacts WHERE jid = %s",
                (jid,),
            )
            row_pg = cur_pg.fetchone()

            if row_pg:
                contact_id = row_pg[0]
                existing_phone = row_pg[1]
                existing_name = row_pg[2]
                should_update_phone = False
                should_update_name = False

                if phone:
                    if not existing_phone:
                        should_update_phone = True
                    elif jid.endswith("@lid"):
                        lid_local = jid.split("@", 1)[0]
                        if existing_phone == lid_local:
                            should_update_phone = True

                if name and not existing_name:
                    should_update_name = True

                if phone and should_update_phone:
                    try:
                        cur_pg.execute(
                            "UPDATE contacts SET phone = %s WHERE id = %s",
                            (phone, contact_id),
                        )
                    except Exception:
                        pass

                if name and should_update_name:
                    try:
                        cur_pg.execute(
                            "UPDATE contacts SET name = %s WHERE id = %s",
                            (name, contact_id),
                        )
                    except Exception:
                        pass
            else:
                cur_pg.execute(
                    "INSERT INTO contacts (jid, phone, name) VALUES (%s, %s, %s) RETURNING id",
                    (jid, phone, name),
                )
                contact_id = cur_pg.fetchone()[0]

            pg.commit()
            pg.close()
            return contact_id
        except Exception as e:
            print("Postgres upsert_contact failed:", e)
            return None

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT id, phone, name FROM contacts WHERE jid = ?", (jid,))
    row = cur.fetchone()

    if row:
        contact_id = row[0]
        existing_phone = row[1]
        existing_name = row[2]
        should_update_phone = False
        should_update_name = False

        if phone:
            if not existing_phone:
                should_update_phone = True
            elif jid.endswith("@lid"):
                lid_local = jid.split("@", 1)[0]
                if existing_phone == lid_local:
                    should_update_phone = True

        if name and not existing_name:
            should_update_name = True

        if phone and should_update_phone:
            try:
                cur.execute(
                    "UPDATE contacts SET phone = ? WHERE id = ?",
                    (phone, contact_id),
                )
            except Exception:
                pass

        if name and should_update_name:
            try:
                cur.execute(
                    "UPDATE contacts SET name = ? WHERE id = ?",
                    (name, contact_id),
                )
            except Exception:
                pass
    else:
        cur.execute(
            "INSERT INTO contacts (jid, phone, name) VALUES (?, ?, ?)",
            (jid, phone, name),
        )
        contact_id = cur.lastrowid

    db.commit()
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
    status: str,
    phone: str | None = None,
    name: str | None = None,
):
    created_at_ms = int(time.time() * 1000)
    timestamp_str = format_timestamp(timestamp)
    created_at_str = format_timestamp(created_at_ms)

    if has_postgres():
        contact_id_pg = upsert_contact(jid, phone, name)

        if contact_id_pg is None:
            print("Postgres insert_message skipped: contact upsert failed")
            return

        try:
            pg = get_pg_db()
            if pg is None:
                return

            cur_pg = pg.cursor()

            cur_pg.execute(
                """
                INSERT INTO messages (
                    message_id,
                    contact_id,
                    direction,
                    message_type,
                    content,
                    media_path,
                    timestamp,
                    status,
                    created_at,
                    timestamp_str,
                    created_at_str
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
                """,
                (
                    message_id,
                    contact_id_pg,
                    direction,
                    message_type,
                    content,
                    media_path,
                    timestamp,
                    status,
                    created_at_ms,
                    timestamp_str,
                    created_at_str,
                ),
            )

            pg.commit()
            pg.close()
        except Exception as e:
            print("Postgres insert_message failed:", e)

        return

    contact_id = upsert_contact(jid, phone, name)

    db = get_db()
    cur = db.cursor()

    cur.execute(
        """
    INSERT OR IGNORE INTO messages (
        message_id, contact_id, direction,
        message_type, content, media_path,
        timestamp, status, created_at,
        timestamp_str, created_at_str
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            message_id,
            contact_id,
            direction,
            message_type,
            content,
            media_path,
            timestamp,
            status,
            created_at_ms,
            timestamp_str,
            created_at_str,
        ),
    )

    db.commit()
    db.close()


def update_message_status(message_id: str, status: str):
    if has_postgres():
        try:
            pg = get_pg_db()
            if pg is None:
                return

            cur_pg = pg.cursor()
            cur_pg.execute(
                """
                UPDATE messages
                SET status = %s
                WHERE message_id = %s
                """,
                (status, message_id),
            )
            pg.commit()
            pg.close()
        except Exception as e:
            print("Postgres update_message_status failed:", e)
        return

    db = get_db()
    cur = db.cursor()

    cur.execute(
        """
    UPDATE messages SET status = ?
    WHERE message_id = ?
    """,
        (status, message_id),
    )

    db.commit()
    db.close()

def update_contact_presence(
    jid: str,
    phone: str | None,
    name: str | None,
    is_online: bool,
    last_seen_at: int | None = None,
):
    now = last_seen_at if last_seen_at is not None else int(time.time() * 1000)
    now_str = format_timestamp(now)

    if has_postgres():
        try:
            pg = get_pg_db()
            if pg is None:
                return

            cur_pg = pg.cursor()
            cur_pg.execute(
                """
                INSERT INTO contacts (
                    jid, phone, name,
                    last_seen_at, is_online,
                    created_at, updated_at,
                    last_seen_at_str, created_at_str, updated_at_str
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (jid) DO UPDATE SET
                    phone = COALESCE(EXCLUDED.phone, contacts.phone),
                    name = COALESCE(EXCLUDED.name, contacts.name),
                    last_seen_at = EXCLUDED.last_seen_at,
                    is_online = EXCLUDED.is_online,
                    updated_at = EXCLUDED.updated_at,
                    last_seen_at_str = EXCLUDED.last_seen_at_str,
                    created_at_str = COALESCE(contacts.created_at_str, EXCLUDED.created_at_str),
                    updated_at_str = EXCLUDED.updated_at_str
                """,
                (
                    jid,
                    phone,
                    name,
                    now,
                    is_online,
                    now,
                    now,
                    now_str,
                    now_str,
                    now_str,
                ),
            )
            pg.commit()
            pg.close()
        except Exception as e:
            print("Postgres update_contact_presence failed:", e)
        return

    db = get_db()
    cur = db.cursor()

    cur.execute(
        """
    INSERT INTO contacts (
        jid, phone, name,
        last_seen_at, is_online,
        created_at, updated_at,
        last_seen_at_str, created_at_str, updated_at_str
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(jid) DO UPDATE SET
        phone = COALESCE(excluded.phone, phone),
        name = COALESCE(excluded.name, name),
        last_seen_at = excluded.last_seen_at,
        is_online = excluded.is_online,
        last_seen_at_str = excluded.last_seen_at_str,
        created_at_str = COALESCE(created_at_str, excluded.created_at_str),
        updated_at = excluded.updated_at,
        updated_at_str = excluded.updated_at_str
    """,
        (
            jid,
            phone,
            name,
            now,
            1 if is_online else 0,
            now,
            now,
            now_str,
            now_str,
            now_str,
        ),
    )

    db.commit()
    db.close()


def insert_media_message(
    message_id: str,
    jid: str,
    direction: str,
    message_type: str,
    content: str | None,
    media_path: str,
    timestamp: int,
    status: str = "delivered",
    phone: str | None = None,
):
    insert_message(
        message_id=message_id,
        jid=jid,
        direction=direction,
        message_type=message_type,
        content=content,
        media_path=media_path,
        timestamp=timestamp,
        status=status,
        phone=phone,
        name=None,
    )
