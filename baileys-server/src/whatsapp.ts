import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion
} from "@whiskeysockets/baileys";
import qrcode from "qrcode";
import * as fs from "fs";
import * as path from "path";
import { getAuthState } from "./state.js";
import { addMessage } from "./messages.js";
import { addReceipt } from "./receipts.js";
import { pushToFastAPI } from "./webhook.js";
import { saveIncomingMedia } from "./media.js";

const AUTH_DIR = path.join(process.cwd(), "auth");
let connectionState: "idle" | "logging_in" | "connected" = "idle"
let lastAuthReset = 0
let isRestarting = false
let connectionPhase: "idle" | "connecting" | "connected" = "idle"
const AUTH_RESET_COOLDOWN_MS = 15_000 // 15 seconds




function resetAuth() {
  try {
    if (fs.existsSync(AUTH_DIR)) {
      fs.rmSync(AUTH_DIR, { recursive: true, force: true });
      console.log("🧹 Auth state reset");
    }
  } catch (err) {
    console.error("Failed to reset auth:", err);
  }
}
/* =========================
   SOCKET & STATE
   ========================= */
let sock: any = null;
let latestQR: string | null = null;

/* =========================
  Get the user details
   ========================= */

let userInfo: { id?: string; name?: string } | null = null

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

export function getUserInfo() {
  return userInfo;
}

export function getQR() {
  return latestQR;
}

export function getAllChats() {
  return Array.from(chatStore.values());
}

export function getLastMessageByJid(jid: string) {
  const chat = chatStore.get(jid)
  if (!chat || !chat.lastMessage) return null

  return {
    jid: chat.jid,
    name: chat.name,
    type: chat.type,
    message: chat.lastMessage,
    timestamp: chat.lastTimestamp
  }
}

export function normalizeUserJid(input: string): string {
  if (input.includes("@")) return input
  return `${input}@s.whatsapp.net`
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
  const { connection, lastDisconnect, qr } = update

  // QR generation
  if (qr) {
    latestQR = await qrcode.toDataURL(qr)
    connectionPhase = "idle"
    return
  }

  // Connection opened
  if (connection === "open") {
    connectionPhase = "connected"
    isRestarting = false

    latestQR = null
    userInfo = state.creds.me ?? null

    console.log("✅ WhatsApp connected")
    if (userInfo) {
      console.log(`👤 Logged in as ${userInfo.name} (${userInfo.id})`)
    }
    return
  }

  // Connection closed
  if (connection === "close") {
    const statusCode =
      (lastDisconnect?.error as any)?.output?.statusCode

    console.log("❌ WhatsApp connection closed:", statusCode)

    // ⛔ Ignore closes while connecting (VERY IMPORTANT)
    if (connectionPhase === "connecting") {
      console.log("⏳ Ignoring close during connection handshake")
      return
    }

    userInfo = null
    latestQR = null

    // 🔴 Logged out for real → reset auth ONCE
    if (statusCode === DisconnectReason.loggedOut) {
      if (isRestarting) {
        console.log("🛑 Restart already in progress, skipping")
        return
      }

      console.log("🔄 Logged out. Resetting auth and requesting new login…")
      isRestarting = true
      connectionPhase = "idle"

      resetAuth()

      setTimeout(() => {
        connectionPhase = "connecting"
        startWhatsApp()
      }, 3000)

      return
    }

    // ⚠️ Network / transient issue → reconnect
    console.log("🔁 Temporary disconnect, reconnecting…")
    if (isRestarting) return

    isRestarting = true
    connectionPhase = "connecting"

    setTimeout(() => {
      startWhatsApp()
    }, 3000)
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

  function extractPhoneFromMessage(msg: any): string | null {
    const jid = msg?.key?.remoteJid as string | undefined;
    if (!jid) return null;

    const remoteJidAlt = (msg.key as any).remoteJidAlt as string | undefined;
    const participantAlt = (msg.key as any).participantAlt as string | undefined;

    if (jid.endsWith("@g.us")) {
      const rawParticipant =
        (participantAlt as string | undefined) ||
        (msg.key.participant as string | undefined);

      if (rawParticipant && rawParticipant.endsWith("@s.whatsapp.net")) {
        return rawParticipant.split("@")[0];
      }

      return null;
    }

    const userJid = (remoteJidAlt as string | undefined) || jid;

    if (userJid && userJid.endsWith("@s.whatsapp.net")) {
      return userJid.split("@")[0];
    }

    return null;
  }

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

      const phone = extractPhoneFromMessage(msg);

      saveIncomingMedia(msg).then((media) => {
        pushToFastAPI({
          type: "media",
          direction: "in",
          from: msg.key.remoteJid,
          phone,
          messageId: msg.key.id,
          messageType: "media",
          filePath: media.filePath,
          fileName: media.fileName,
          mimeType: media.mimeType,
          caption: media.caption,
          timestamp: Date.now()
        });
      }).catch(() => {});

      return;
    }


    if (!msg?.message || msg.key.fromMe) return;

    const text =
      msg.message.conversation ||
      msg.message.extendedTextMessage?.text;

    if (!text) return;

    const jid = msg.key.remoteJid!;
    const phone = extractPhoneFromMessage(msg);

    const payload = {
      from: jid,
      phone,
      message: text,
      timestamp: Date.now()
    };

    pushToFastAPI({
      type: "message",
      messageId: msg.key.id,
      ...payload
    });

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
    for (const msg of m.messages) {

        if (msg.key?.remoteJid === "status@broadcast") {
          const jid = msg.key.remoteJid;
          /*const jid = msg.key.participant_lid || msg.key.participant;*/
          const phone = msg.key.participant?.split("@")[0] || null;
          const name = msg.pushName || null;

          pushToFastAPI({
            type: "presence",
            jid,
            phone,
            name,
            offline: msg.key.offline === "1" ? true : false,
            timestamp: Date.now()
          });}}
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

