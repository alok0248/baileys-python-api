/*Stores incoming WhatsApp messages in memory (last 100).*/ 

export interface IncomingMessage {
  from: string; // raw jid
  phone?: string | null; // extracted phone if possible
  message: string;
  timestamp: number;
}

const messages: IncomingMessage[] = [];

export function addMessage(msg: IncomingMessage) {
  messages.push(msg);
  if (messages.length > 100) messages.shift();
}

export function getMessages() {
  return messages;
}