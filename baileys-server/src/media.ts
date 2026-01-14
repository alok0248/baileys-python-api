import * as fs from "fs";
import * as path from "path";
import { downloadContentFromMessage } from "@whiskeysockets/baileys";

const BASE_MEDIA_DIR = path.resolve("media");
const INCOMING_DIR = path.join(BASE_MEDIA_DIR, "incoming");
const OUTGOING_DIR = path.join(BASE_MEDIA_DIR, "outgoing");

// ensure folders exist
fs.mkdirSync(INCOMING_DIR, { recursive: true });
fs.mkdirSync(OUTGOING_DIR, { recursive: true });

/**
 * Map WhatsApp message keys to Baileys media types
 */
function getMediaType(msg: any):
  | "image"
  | "video"
  | "audio"
  | "document"
  | "sticker" {

  if (msg.message?.imageMessage) return "image";
  if (msg.message?.videoMessage) return "video";
  if (msg.message?.audioMessage) return "audio";
  if (msg.message?.documentMessage) return "document";
  if (msg.message?.stickerMessage) return "sticker";

  throw new Error("Unsupported media type");
}

/**
 * Save incoming media message to disk
 */
export async function saveIncomingMedia(msg: any) {
  const mediaType = getMediaType(msg);
  const mediaMessage = msg.message[`${mediaType}Message`];

  const stream = await downloadContentFromMessage(
    mediaMessage,
    mediaType
  );

  const fileName = `${Date.now()}_${msg.key.id}`;
  const filePath = path.join(INCOMING_DIR, fileName);

  const buffer: Buffer[] = [];
  for await (const chunk of stream) {
    buffer.push(chunk);
  }

  fs.writeFileSync(filePath, Buffer.concat(buffer));

  return {
    fileName,
    filePath,
    mimeType: mediaMessage.mimetype || null
  };
}
