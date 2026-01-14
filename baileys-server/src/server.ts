import express from "express";
import { startWhatsApp, getQR,getSock } from "./whatsapp.js";
import { getMessages } from "./messages.js";
import { getReceipts } from "./receipts.js";
import { getUserDetails, getGroupDetails, 
        getJidFromPhone,getAllJoinedGroups
 } from "./contacts.js";
import { getAllChats } from "./chats.js";
const app = express();
app.use(express.json());
import * as fs from "fs";
import * as path from "path";
import mime from "mime-types";



app.get("/qr", (req, res) => {
  const qr = getQR();
  if (!qr) {
    return res.json({ status: "ready" });
  }
  res.json({ qr });
});

app.get("/health", (_, res) => {
  res.json({ status: "ok" });
});

const PORT = 3000;

  // Get user details (1-to-1)
  app.get("/user/:phone", async (req, res) => {
    try {
      const phone = req.params.phone;
      const jid = `${phone}@s.whatsapp.net`;

      const info = await getUserDetails(jid);
      res.json(info);
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // Get group details
  app.get("/group/:jid", async (req, res) => {
    try {
      const jid = req.params.jid;
      const info = await getGroupDetails(jid);
      res.json(info);
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });
  // Resolve JID from phone number
    app.get("/jid/:phone", async (req, res) => {
      try {
        const phone = req.params.phone;
        const info = await getJidFromPhone(phone);
        res.json(info);
      } catch (e: any) {
        res.status(500).json({ error: e.message });
      }
    });
    // Get all joined groups
      app.get("/groups", async (req, res) => {
        try {
          const groups = await getAllJoinedGroups();
          res.json(groups);
        } catch (e: any) {
          res.status(500).json({ error: e.message });
        }
      });

      // Get all chat details
    app.get("/chats", (req, res) => {
      try {
        const chats = getAllChats();
        res.json(chats);
      } catch (e: any) {
        res.status(500).json({ error: e.message });
      }
    });








    
app.listen(PORT, async () => {
  console.log(`🚀 Baileys server running on ${PORT}`);
  await startWhatsApp();
});


app.post("/send", async (req, res) => {
  const { to, message } = req.body;
  
  
  if (!to || !message) {
    return res.status(400).json({ error: "to and message required" });
  }

  try {
    const sock = getSock();

    if (!sock) {
      return res.status(503).json({ error: "WhatsApp not connected yet" });
    }

    await sock.sendMessage(`${to}@s.whatsapp.net`, { text: message });

    res.json({ status: "sent" });
  } catch {
    res.status(500).json({ error: "send failed" });
  }
});

app.get("/messages", (req, res) => {
  res.json(getMessages());
});


app.get("/receipts", (req, res) => {
  res.json(getReceipts());
});


app.post("/send/media", async (req, res) => {
  try {
    const { to, filePath, caption } = req.body;

    const sock = getSock();
    if (!sock) {
      return res.status(503).json({ error: "WhatsApp not connected" });
    }

    if (!to || !filePath) {
      return res.status(400).json({ error: "'to' and 'filePath' are required" });
    }

    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: "File not found" });
    }

    const jid = normalizeJid(to);
    const buffer = fs.readFileSync(filePath);

    const mimeType = mime.lookup(filePath) || "application/octet-stream";

    let message: any;

    if (mimeType.startsWith("image/")) {
      message = {
        image: buffer,
        mimetype: mimeType,
        caption
      };
    } else if (mimeType.startsWith("video/")) {
      message = {
        video: buffer,
        mimetype: mimeType,
        caption
      };
    } else if (mimeType.startsWith("audio/")) {
      message = {
        audio: buffer,
        mimetype: mimeType
      };
    } else {
      message = {
        document: buffer,
        mimetype: mimeType,
        fileName: path.basename(filePath),
        caption
      };
    }

    await sock.sendMessage(jid, message);

    res.json({ status: "sent" });

  } catch (err: any) {
    console.error("❌ Media send failed:", err);
    res.status(500).json({ error: err.message });
  }
});

function normalizeJid(to: string): string {
  if (!to) {
    throw new Error("Recipient 'to' is missing");
  }

  // already a JID
  if (to.includes("@")) {
    return to;
  }

  // phone number → WhatsApp user JID
  return `${to}@s.whatsapp.net`;
}
