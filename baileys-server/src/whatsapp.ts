import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion
} from "@whiskeysockets/baileys";
import qrcode from "qrcode";

import { getAuthState } from "./state.js";
import { addMessage } from "./messages.js";
import { addReceipt } from "./receipts.js";
import { pushToFastAPI } from "./webhook.js";
import { saveIncomingMedia } from "./media.js";

/* =========================
   SOCKET & STATE
   ========================= */
let sock: any = null;
let latestQR: string | null = null;

/* =========================
   CUSTOM CHAT STORE (SAFE)
   ========================= */
const chatStore = new Map<string, any>();

/* =========================
   GETTERS
   ========================= */
export function getSock() {
  return sock;
}

export function getQR() {
  return latestQR;
}

export function getAllChats() {
  return Array.from(chatStore.values());
}

/* =========================
   MAIN START FUNCTION
   ========================= */
export async function startWhatsApp() {
  const { state, saveCreds } = await getAuthState();
  const { version } = await fetchLatestBaileysVersion();

  if (!state) {
    throw new Error("Auth state is undefined");
  }

  sock = makeWASocket({
    version,
    auth: state,
    printQRInTerminal: false
  });

  sock.ev.on("creds.update", saveCreds);

  /* =========================
     CONNECTION / QR
     ========================= */
  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      latestQR = await qrcode.toDataURL(qr);
    }

    if (connection === "close") {
      const shouldReconnect =
        (lastDisconnect?.error as any)?.output?.statusCode !==
        DisconnectReason.loggedOut;

      if (shouldReconnect) {
        startWhatsApp();
      }
    }

    if (connection === "open") {
      console.log("✅ WhatsApp logged in successfully");
      latestQR = null;
    }
  });

  /* =========================
     CHAT METADATA UPDATES
     ========================= */
  sock.ev.on("chats.set", ({ chats }) => {
    for (const c of chats) {
      chatStore.set(c.id, {
        jid: c.id,
        type: c.id.endsWith("@g.us") ? "group" : "user",
        name: c.name || null,
        unreadCount: c.unreadCount ?? 0,
        archived: !!c.archive,
        muted: !!c.muteEndTime,
        lastMessage: null,
        lastTimestamp: null
      });
    }
  });

  /* =========================
     INCOMING MESSAGES
     ========================= */
  sock.ev.on("messages.upsert", (m) => {
    const msg = m.messages[0];
    // MEDIA MESSAGE
    if (msg.message?.imageMessage ||
        msg.message?.videoMessage ||
        msg.message?.audioMessage ||
        msg.message?.documentMessage) {

      saveIncomingMedia(msg).then((media) => {
        pushToFastAPI({
          type: "media",
          from: msg.key.remoteJid,
          file: media.fileName,
          mimeType: media.mimeType,
          timestamp: Date.now()
        });
      });

      return;
    }


    if (!msg?.message || msg.key.fromMe) return;

    const text =
      msg.message.conversation ||
      msg.message.extendedTextMessage?.text;

    if (!text) return;

    const jid = msg.key.remoteJid!;
    let phone: string | null = null;

    if (jid.endsWith("@s.whatsapp.net")) {
      phone = jid.split("@")[0];
    }

    if (jid.endsWith("@g.us") && msg.key.participant) {
      phone = msg.key.participant.split("@")[0];
    }

    const payload = {
      from: jid,
      phone,
      message: text,
      timestamp: Date.now()
    };

    // update chat store
    const chat = chatStore.get(jid) || {
      jid,
      type: jid.endsWith("@g.us") ? "group" : "user",
      name: null,
      unreadCount: 0,
      archived: false,
      muted: false
    };

    chat.lastMessage = text;
    chat.lastTimestamp = Date.now();
    chatStore.set(jid, chat);

    addMessage(payload);
    pushToFastAPI(payload);
  });

  /* =========================
     DELIVERY / READ RECEIPTS
     ========================= */
  sock.ev.on("message-receipt.update", (updates) => {
    for (const u of updates) {
      if (!u.key?.id) continue;

      let status: "delivered" | "read" | null = null;

      if (u.readTimestamp) status = "read";
      else if (u.receiptTimestamp) status = "delivered";

      if (!status) continue;

      const payload = {
        messageId: u.key.id,
        to: u.key.remoteJid!,
        status,
        timestamp: Date.now()
      };

      addReceipt(payload);
      pushToFastAPI({ type: "receipt", ...payload });
    }
  });
}

