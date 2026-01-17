from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel
import requests
import base64
import io
import os
import json
import shutil
import time
import uuid
import uvicorn
from dotenv import load_dotenv
from db import init_db
from db_ops import insert_message, update_message_status
from db_ops import update_contact_presence
from config import NODE_BASE_URL
from db_ops import insert_media_message


ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(ENV_PATH):
    load_dotenv(ENV_PATH)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "db_config.json")

try:
    with open(CONFIG_FILE, "r") as f:
        _config = json.load(f)
except Exception:
    _config = {}

_base_path = _config.get("base_path")
_user_name = _config.get("user")

if _base_path and _user_name:
    OUTGOING_BASE_DIR = os.path.join(_base_path, _user_name, "outgoing")
elif _base_path:
    OUTGOING_BASE_DIR = os.path.join(_base_path, "outgoing")
else:
    OUTGOING_BASE_DIR = None

if OUTGOING_BASE_DIR:
    os.makedirs(OUTGOING_BASE_DIR, exist_ok=True)


def normalize_outgoing_path(file_path: str) -> str:
    src = os.path.abspath(file_path)

    if not OUTGOING_BASE_DIR:
        return src

    name = os.path.basename(src)
    dst = os.path.join(OUTGOING_BASE_DIR, name)

    if src == dst:
        return dst

    try:
        shutil.copy2(src, dst)
        return dst
    except Exception:
        return src


app = FastAPI(
    title="Baileys FastAPI Bridge",
    description="FastAPI bridge for Baileys WhatsApp server",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
init_db()


# ============================================================
# 🔍 HEALTH
# ============================================================

@app.get("/health")
def health():
    """Health check for FastAPI"""
    return {"status": "fastapi-ok"}


# ============================================================
# 📲 QR CODE (LOGIN)
# ============================================================

@app.get("/qr")
def fetch_qr():
    """Fetch raw QR JSON from Baileys"""
    try:
        resp = requests.get(f"{NODE_BASE_URL}/qr", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/qr/image")
def qr_image():
    """Return QR code as PNG image"""
    data = fetch_qr()

    if "qr" not in data:
        raise HTTPException(status_code=404, detail="QR not available")

    b64_data = data["qr"].split(",")[1]
    img_bytes = base64.b64decode(b64_data)

    return StreamingResponse(
        io.BytesIO(img_bytes),
        media_type="image/png"
    )


@app.get("/qr/view", response_class=HTMLResponse)
def qr_view():
    """Render QR code nicely in browser"""
    data = fetch_qr()

    if "qr" not in data:
        return """
        <html>
            <body style="font-family:Arial;text-align:center;margin-top:50px;">
                <h2>✅ WhatsApp already logged in</h2>
            </body>
        </html>
        """

    return f"""
    <html>
        <head>
            <title>WhatsApp Login</title>
        </head>
        <body style="font-family:Arial;text-align:center;background:#f4f6f8;">
            <div style="
                display:inline-block;
                margin-top:50px;
                padding:30px;
                background:white;
                border-radius:10px;
                box-shadow:0 0 10px rgba(0,0,0,0.1);
            ">
                <h2>📲 Scan QR with WhatsApp</h2>
                <img src="{data['qr']}" style="margin-top:20px;" />
                <p style="color:#666;margin-top:20px;">
                    Open WhatsApp → Linked Devices → Scan QR
                </p>
            </div>
        </body>
    </html>
    """


# ============================================================
# 💬 MESSAGING
# ============================================================

class SendMessage(BaseModel):
    to: str
    message: str


@app.post("/send")
def send_message(data: SendMessage):
    """Send a text message"""
    r = requests.post(
        f"{NODE_BASE_URL}/send",
        json=data.dict(),
        timeout=5
    )
    message_id =  str(uuid.uuid4())
    now = int(time.time() * 1000)
    # 🔹 Save outgoing message FIRST
    insert_message(
        message_id=message_id,
        jid=data.to,
        direction="out",
        message_type="text",
        content=data.message,
        media_path=None,
        timestamp=now,
        status="sent"
    )

    r.raise_for_status()
    return {
        "status": "sent",
        "messageId": message_id
    }


@app.get("/messages")
def get_messages():
    """Get received messages"""
    r = requests.get(f"{NODE_BASE_URL}/messages", timeout=5)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, list):
        for msg in data:
            if not isinstance(msg, dict):
                continue
            phone = msg.get("phone")
            if phone:
                original_from = msg.get("from")
                if original_from and "jid" not in msg:
                    msg["jid"] = original_from
                msg["from"] = phone

    return data


# ============================================================
# 📎 MEDIA
# ============================================================

class SendMedia(BaseModel):
    to: str
    filePath: str
    caption: str | None = None


@app.post("/send/media")
def send_media(data: SendMedia):
    message_id = str(uuid.uuid4())
    now = int(time.time() * 1000)
    resolved_path = normalize_outgoing_path(data.filePath)

    r = requests.post(
        f"{NODE_BASE_URL}/send/media",
        json={
            "to": data.to,
            "filePath": resolved_path,
            "caption": data.caption
        },
        timeout=30
    )
    r.raise_for_status()
    insert_message(
        message_id=message_id,
        jid=data.to,
        direction="out",
        message_type="media",
        content=data.caption,
        media_path=resolved_path,
        timestamp=now,
        status="sent"
    )
    return {
        "status": "sent",
        "messageId": message_id
    }


@app.get("/media/{filename}")
def download_media(filename: str):
    """Download received media"""
    r = requests.get(f"{NODE_BASE_URL}/media/{filename}", stream=True)
    r.raise_for_status()
    return StreamingResponse(
        r.raw,
        media_type=r.headers.get("content-type", "application/octet-stream")
    )


# ============================================================
# 📨 RECEIPTS
# ============================================================

@app.get("/receipts")
def get_receipts():
    """Get delivery/read receipts"""
    r = requests.get(f"{NODE_BASE_URL}/receipts", timeout=5)
    r.raise_for_status()
    return r.json()


@app.post("/webhook/receipt")
async def webhook_receipt(request: Request):
    payload = await request.json()

    update_message_status(
        message_id=payload.get("messageId"),
        status=payload.get("status")
    )

    print("📬 Updated receipt:", payload)
    return {"status": "ok"}



# ============================================================
# 🌐 WEBHOOKS (INCOMING EVENTS)
# ============================================================

@app.post("/webhook/message")
async def webhook_message(request: Request):
    payload = await request.json()

    if payload.get("type") in ("presence", "media") or payload.get("from") == "status@broadcast":
        return {"status": "ignored"}

    content_text = (
        payload.get("message")
        or payload.get("text")
        or payload.get("body")
    )

    insert_message(
        message_id=payload.get("messageId"),
        jid=payload.get("from"),
        direction="in",
        message_type="text",
        content=content_text,
        media_path=None,
        timestamp=payload.get("timestamp"),
        status="delivered",
        phone=payload.get("phone"),
        name=payload.get("name"),
    )

    print("📩 Stored message:", payload)
    return {"status": "ok"}


# ============================================================
# 👤 CONTACTS / CHATS
# ============================================================

@app.get("/user/{phone}")
def get_user(phone: str):
    """Get user details by phone"""
    r = requests.get(f"{NODE_BASE_URL}/user/{phone}", timeout=5)
    r.raise_for_status()
    return r.json()


@app.get("/group/{group_jid}")
def get_group(group_jid: str):
    """Get group details"""
    r = requests.get(f"{NODE_BASE_URL}/group/{group_jid}", timeout=5)
    r.raise_for_status()
    return r.json()


@app.get("/jid/{phone}")
def get_jid(phone: str):
    """Resolve JID from phone number"""
    r = requests.get(f"{NODE_BASE_URL}/jid/{phone}", timeout=5)
    r.raise_for_status()
    return r.json()


@app.get("/groups")
def get_groups():
    """Get all joined groups"""
    r = requests.get(f"{NODE_BASE_URL}/groups", timeout=5)
    r.raise_for_status()
    return r.json()


@app.get("/chats")
def get_chats():
    """Get all chats"""
    r = requests.get(f"{NODE_BASE_URL}/chats", timeout=5)
    r.raise_for_status()
    return r.json()


@app.post("/sync/contacts")
def sync_contacts():
    try:
        r = requests.get(f"{NODE_BASE_URL}/chats", timeout=15)
        r.raise_for_status()
        chats = r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not isinstance(chats, list):
        return {"synced": 0}

    synced = 0

    for chat in chats:
        if not isinstance(chat, dict):
            continue

        jid = chat.get("jid")

        if not isinstance(jid, str) or not jid or jid == "status@broadcast":
            continue

        name = chat.get("name")
        last_ts = chat.get("lastTimestamp")

        phone = None
        if jid.endswith("@s.whatsapp.net"):
            phone = jid.split("@")[0]

        update_contact_presence(
            jid=jid,
            phone=phone,
            name=name,
            is_online=False,
            last_seen_at=last_ts if isinstance(last_ts, int) else None,
        )

        synced += 1

    return {"synced": synced}


# ============================================================
# 🧠 WHATSAPP META
# ============================================================

@app.get("/whatsapp/me")
def whatsapp_me():
    """Get logged-in WhatsApp user"""
    try:
        r = requests.get(f"{NODE_BASE_URL}/me", timeout=5)
        if r.status_code == 404:
            return {"logged_in": False}
        r.raise_for_status()
        return {
            "logged_in": True,
            "user": r.json()
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/whatsapp/qr")
def get_qr():
    """Unified QR status endpoint"""
    r = requests.get(f"{NODE_BASE_URL}/qr", timeout=5)
    data = r.json()

    if data.get("status") == "ready":
        return {"status": "connected"}

    if not data.get("qr"):
        return {"status": "login_required"}

    return data


@app.get("/whatsapp/last-message/{user}")
def whatsapp_last_message(user: str):
    """Get last message of a user or group"""
    try:
        r = requests.get(f"{NODE_BASE_URL}/last-message/{user}", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError:
        return {"error": "No messages found"}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/presence")
async def webhook_presence(request: Request):
    payload = await request.json()

    update_contact_presence(
        jid=payload.get("jid"),
        phone=payload.get("phone"),
        name=payload.get("name"),
        is_online=not payload.get("offline", False)
    )

    print("👤 Presence updated:", payload)
    return {"status": "ok"}
@app.post("/webhook/media")
async def webhook_media(request: Request):
    payload = await request.json()

    caption_text = (
        payload.get("caption")
        or payload.get("message")
        or payload.get("text")
        or payload.get("body")
    )

    insert_media_message(
        message_id=payload.get("messageId"),
        jid=payload.get("from"),
        direction=payload.get("direction", "in"),
        message_type=payload.get("messageType", "media"),
        content=caption_text,
        media_path=payload.get("filePath"),
        timestamp=payload.get("timestamp"),
        status="delivered",
        phone=payload.get("phone"),
    )

    print("🖼️ Media stored:", payload.get("filePath"))
    return {"status": "ok"}


if __name__ == "__main__":
    fastapi_host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    fastapi_port = int(os.getenv("FASTAPI_PORT", "3002"))

    uvicorn.run(
        "main:app",
        host=fastapi_host,
        port=fastapi_port,
        reload=False
    )
