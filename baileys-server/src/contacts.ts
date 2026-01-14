import { getSock } from "./whatsapp.js";

/**
 * Get user (1-to-1) details
 */
export async function getUserDetails(jid: string) {
  const sock = getSock();
  if (!sock) throw new Error("WhatsApp not connected");

  const [result] = await sock.onWhatsApp(jid);

  if (!result) {
    return null;
  }

  return {
    jid: result.jid,
    exists: result.exists,
    isBusiness: result.isBusiness ?? false
  };
}

/**
 * Get group details
 */
export async function getGroupDetails(groupJid: string) {
  const sock = getSock();
  if (!sock) throw new Error("WhatsApp not connected");

  const metadata = await sock.groupMetadata(groupJid);

  return {
    id: metadata.id,
    subject: metadata.subject,
    owner: metadata.owner,
    size: metadata.participants.length,
    participants: metadata.participants.map((p: any) => ({
      jid: p.id,
      phone: p.id.endsWith("@s.whatsapp.net")
        ? p.id.split("@")[0]
        : null,
      isAdmin: p.admin === "admin" || p.admin === "superadmin"
    }))
  };
}

/**
 * Resolve JID from phone number
 */
export async function getJidFromPhone(phone: string) {
  const sock = getSock();
  if (!sock) throw new Error("WhatsApp not connected");

  const jid = `${phone}@s.whatsapp.net`;
  const [result] = await sock.onWhatsApp(jid);

  if (!result) {
    return {
      phone,
      jid,
      exists: false
    };
  }

  return {
    phone,
    jid: result.jid,
    exists: result.exists,
    isBusiness: result.isBusiness ?? false
  };
}


/**
 * Get all joined WhatsApp groups
 */
export async function getAllJoinedGroups() {
  const sock = getSock();
  if (!sock) throw new Error("WhatsApp not connected");

  const groups = await sock.groupFetchAllParticipating();

  return Object.values(groups).map((g: any) => ({
    jid: g.id,
    subject: g.subject,
    size: g.participants?.length ?? 0,
    isAdmin: g.participants?.some(
      (p: any) =>
        p.id === sock.user?.id &&
        (p.admin === "admin" || p.admin === "superadmin")
    ) ?? false
  }));
}

