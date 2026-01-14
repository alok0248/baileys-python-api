import { getAllChats as getChatsFromWhatsApp } from "./whatsapp.js";

/**
 * Get all chat details (users + groups)
 * Source: custom in-memory chat store (store-free, Baileys-safe)
 */
export function getAllChats() {
  return getChatsFromWhatsApp();
}
