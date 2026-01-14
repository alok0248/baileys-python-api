from fastapi import FastAPI, HTTPException,Request
from fastapi.responses import StreamingResponse, HTMLResponse
import requests
import base64
import io
from config import NODE_BASE_URL
from pydantic import BaseModel
app = FastAPI(title="Baileys FastAPI Bridge")


@app.get("/qr")
def fetch_qr():
    try:
        resp = requests.get(f"{NODE_BASE_URL}/qr", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=str(e))


# 🆕 1️⃣ Return QR as IMAGE
@app.get("/qr/image")
def qr_image():
    data = fetch_qr()

    if "qr" not in data:
        raise HTTPException(status_code=404, detail="QR not available")

    # Remove data:image/png;base64,
    b64_data = data["qr"].split(",")[1]
    img_bytes = base64.b64decode(b64_data)

    return StreamingResponse(
        io.BytesIO(img_bytes),
        media_type="image/png"
    )


# 🆕 2️⃣ Render QR in Browser
@app.get("/qr/view", response_class=HTMLResponse)
def qr_view():
    data = fetch_qr()

    if "qr" not in data:
        return "<h2>✅ WhatsApp already logged in</h2>"

    return f"""
    <html>
        <head>
            <title>WhatsApp QR</title>
        </head>
        <body style="text-align:center; font-family:Arial;">
            <h2>Scan QR with WhatsApp</h2>
            <img src="{data['qr']}" />
        </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "fastapi-ok"}


class SendMessage(BaseModel):
    to: str
    message: str

@app.post("/send")
def send_message(data: SendMessage):
    r = requests.post(
        f"{NODE_BASE_URL}/send",
        json=data.dict(),
        timeout=5
    )
    r.raise_for_status()
    return r.json()

@app.get("/messages")
def get_messages():
    r = requests.get(f"{NODE_BASE_URL}/messages", timeout=5)
    r.raise_for_status()
    return r.json()


@app.post("/webhook/message")
async def webhook_message(request: Request):
    payload = await request.json()

    # For now, just log it (or store later)
    print("📩 Webhook message received:", payload)

    return {"status": "ok"}

@app.post("/webhook/receipt")
async def webhook_receipt(request: Request):
    payload = await request.json()
    print("📬 Receipt webhook:", payload)
    return {"status": "ok"}

@app.get("/receipts")
def get_receipts():
    r = requests.get(f"{NODE_BASE_URL}/receipts", timeout=5)
    r.raise_for_status()
    return r.json()


@app.get("/user/{phone}")
def get_user(phone: str):
    r = requests.get(f"{NODE_BASE_URL}/user/{phone}", timeout=5)
    r.raise_for_status()
    return r.json()

@app.get("/group/{group_jid}")
def get_group(group_jid: str):
    r = requests.get(f"{NODE_BASE_URL}/group/{group_jid}", timeout=5)
    r.raise_for_status()
    return r.json()

@app.get("/jid/{phone}")
def get_jid(phone: str):
    r = requests.get(f"{NODE_BASE_URL}/jid/{phone}", timeout=5)
    r.raise_for_status()
    return r.json()


@app.get("/groups")
def get_groups():
    r = requests.get(f"{NODE_BASE_URL}/groups", timeout=5)
    r.raise_for_status()
    return r.json()


@app.get("/chats")
def get_chats():
    r = requests.get(f"{NODE_BASE_URL}/chats", timeout=5)
    r.raise_for_status()
    return r.json()


class SendMedia(BaseModel):
    to: str
    filePath: str
    caption: str | None = None


@app.post("/send/media")
def send_media(data: SendMedia):
    r = requests.post(
        f"{NODE_BASE_URL}/send/media",
        json=data.dict(),
        timeout=10
    )
    r.raise_for_status()
    return r.json()

@app.get("/media/{filename}")
def download_media(filename: str):
    r = requests.get(f"{NODE_BASE_URL}/media/{filename}", stream=True)
    r.raise_for_status()
    return StreamingResponse(
        r.raw,
        media_type=r.headers.get("content-type", "application/octet-stream")
    )
