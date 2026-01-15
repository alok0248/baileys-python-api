from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
import requests
import base64
import io
from db import init_db
from db_ops import insert_message, update_message_status
from db_ops import insert_message
import time
import uuid
from db_ops import update_contact_presence
from config import NODE_BASE_URL

app = FastAPI(
    title="Baileys FastAPI Bridge",
    description="FastAPI bridge for Baileys WhatsApp server",
    version="1.0.0"
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
    message_id = str(uuid.uuid4())
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
    return r.json()


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
    """Send media (image/video/audio/document)"""
    r = requests.post(
        f"{NODE_BASE_URL}/send/media",
        json=data.model_dump(),
        timeout=30
    )
    r.raise_for_status()
    # 🔹 Store outgoing media message
    insert_message(
        message_id=message_id,
        jid=data.to,
        direction="out",
        message_type="media",
        content=data.caption,
        media_path=data.filePath,
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

    insert_message(
        message_id=payload.get("messageId"),
        jid=payload.get("from"),
        direction="in",
        message_type="text",
        content=payload.get("message"),
        media_path=None,
        timestamp=payload.get("timestamp"),
        status="delivered"
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