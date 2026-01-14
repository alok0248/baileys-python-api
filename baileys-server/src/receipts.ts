export interface MessageReceipt {
  messageId: string;
  to: string;
  status: "sent" | "delivered" | "read";
  timestamp: number;
}

const receipts: MessageReceipt[] = [];

export function addReceipt(r: MessageReceipt) {
  receipts.push(r);
  if (receipts.length > 200) receipts.shift();
}

export function getReceipts() {
  return receipts;
}
