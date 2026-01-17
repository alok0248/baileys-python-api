import fetch from "node-fetch";

/**
 * Webhook endpoints
 * (FastAPI side already has these)
 */
const FASTAPI_HOST = process.env.FASTAPI_HOST || "localhost";
const FASTAPI_PORT = process.env.FASTAPI_PORT || "3002";
const FASTAPI_BASE = `http://${FASTAPI_HOST}:${FASTAPI_PORT}`;
const FASTAPI_MESSAGE_WEBHOOK = `${FASTAPI_BASE}/webhook/message`;
const FASTAPI_RECEIPT_WEBHOOK = `${FASTAPI_BASE}/webhook/receipt`;
const FASTAPI_PRESENCE_WEBHOOK = `${FASTAPI_BASE}/webhook/presence`;
const FASTAPI_MEDIA_WEBHOOK = `${FASTAPI_BASE}/webhook/media`;

/**
 * Push events to FastAPI
 * - Non-blocking
 * - Safe if FastAPI is down
 * - Supports message & receipt
 */
export async function pushToFastAPI(payload: any) {
  try {
    let url = FASTAPI_MESSAGE_WEBHOOK;

    if (payload?.type === "receipt") {
      url = FASTAPI_RECEIPT_WEBHOOK;
    } else if (payload?.type === "presence") {
      url = FASTAPI_PRESENCE_WEBHOOK;
    } else if (payload?.type === "media") {
      url = FASTAPI_MEDIA_WEBHOOK;
    }

    await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  } catch (err) {
    // IMPORTANT: never crash WhatsApp because webhook failed
    console.error("⚠️ Webhook push failed");
  }
}
