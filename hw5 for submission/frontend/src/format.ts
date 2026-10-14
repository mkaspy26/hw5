// Small formatting helpers shared by the components.

export const money = (n: number | null | undefined) =>
  n === null || n === undefined
    ? "—"
    : n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

export const time = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" });

// Plain-English meaning of each database ticket status.
export const STATUS_TEXT: Record<string, string> = {
  open: "open: nobody has worked on it yet",
  in_progress: "in_progress: the team started but isn't done",
  waiting_on_vendor: "waiting_on_vendor: paid for; waiting for the vendor to deliver",
  waiting_on_approval: "waiting_on_approval: a human must approve a payment, purchase, or discount",
  waiting_on_customer: "waiting_on_customer: waiting for the customer's answer",
  resolved: "resolved: nothing left to do",
};

export const TICKET_TYPE: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Discount request",
};

// Compact one-line view of tool arguments: get_ticket(ticket_id=101)
export const args = (a: Record<string, unknown> | null) =>
  a ? Object.entries(a).map(([k, v]) => `${k}=${typeof v === "string" ? JSON.stringify(v) : String(v)}`).join(", ") : "";

export const pretty = (v: unknown) => {
  if (typeof v === "string") {
    try {
      return JSON.stringify(JSON.parse(v), null, 2);
    } catch {
      return v;
    }
  }
  return JSON.stringify(v, null, 2);
};
