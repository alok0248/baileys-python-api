import * as fs from "fs";
import * as path from "path";
import { INCOMING_MEDIA_DIR } from "./mediaConfig.js";
import { downloadContentFromMessage } from "@whiskeysockets/baileys";

// USE CONFIGURED PATH ONLY
fs.mkdirSync(INCOMING_MEDIA_DIR, { recursive: true });

/**
 * Map WhatsApp message keys to Baileys media types
 */
/**
 * Safely determine file extension for media
 */
function getExtension(mediaMessage: any, mediaType: string): string {
  // If WhatsApp provides original filename (documents)
  if (mediaMessage.fileName) {
    const ext = path.extname(mediaMessage.fileName);
    if (ext) return ext.replace(".", "");
  }

  // If mimetype exists (most media)
  if (mediaMessage.mimetype) {
    const parts = mediaMessage.mimetype.split("/");
    if (parts.length === 2) {
      return parts[1];
    }
  }

  // Safe fallbacks
  if (mediaType === "audio") return "ogg";
  if (mediaType === "sticker") return "webp";
  if (mediaType === "video") return "mp4";
  if (mediaType === "image") return "jpg";

  return "bin";
}

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
  const caption =
    mediaMessage.caption ||
    mediaMessage.text ||
    null;

  const stream = await downloadContentFromMessage(
    mediaMessage,
    mediaType
  );

const ext = getExtension(mediaMessage, mediaType);
const fileName = `${Date.now()}_${mediaType}.${ext}`;
const filePath = path.join(INCOMING_MEDIA_DIR, fileName);



  const buffer: Buffer[] = [];
  for await (const chunk of stream) {
    buffer.push(chunk);
  }

  fs.writeFileSync(filePath, Buffer.concat(buffer));

  return {
    fileName,
    filePath,
    mimeType: mediaMessage.mimetype || null,
    caption
  };
}
