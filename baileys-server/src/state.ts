import { useMultiFileAuthState } from "@whiskeysockets/baileys";

export async function getAuthState() {
  return await useMultiFileAuthState("auth_info");
}
