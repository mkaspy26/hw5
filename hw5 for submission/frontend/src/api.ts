// Every call the dashboard makes to the FastAPI backend (backend/main.py).

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export type AgentName = "Boss" | "Inventory" | "Accounting" | "Facilities" | "Customer Service";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  status: string; // database status, e.g. open, waiting_on_approval, resolved
  created_at: string;
  resolved: boolean;
  state: "open" | "resolved";
}

export interface Cash {
  account: string;
  balance: number;
  as_of: string;
  desk_date: string;
}

export interface Approval {
  id: number;
  kind: "rent" | "invoice" | "purchase";
  ref_id: number | null;
  vendor_id: number | null;
  sku: string | null;
  size: string | null;
  qty: number | null;
  amount: number;
  account: string;
  ticket_id: number | null;
  requested_by: string;
  reason: string;
  status: "pending" | "approved" | "declined";
  created_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_note: string | null;
  payment_id: number | null;
}

export interface AgentReport {
  agent?: AgentName;
  ticket_id?: number;
  summary?: string;
  final_status?: string;
  actions_taken?: string[];
  needs_human?: string[];
  recommendations?: string[];
  customer_reply_draft?: string | null;
  error?: string;
}

export interface AgentEvent {
  id: number;
  ts: string;
  run_id: string;
  ticket_id: number | null;
  agent: AgentName;
  event: string;
  delegation_chain: AgentName[];
  said: string | null;
  tools: { tool: string; args: Record<string, unknown> | null }[];
  tool_results: { tool: string; result: unknown }[];
  output?: AgentReport & Record<string, unknown>;
}

export interface Run {
  run_id: string;
  ticket_id: number;
  status: "running" | "done" | "error";
  started_at: string;
  finished_at?: string;
  outcome?: AgentReport;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_URL + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : `${res.status} ${res.statusText}`);
  return body as T;
}

export const api = {
  tickets: () => call<{ desk_date: string; tickets: Ticket[] }>("/tickets"),
  runTicket: (id: number) => call<Run>(`/tickets/${id}/run`, { method: "POST" }),
  run: (runId: string) => call<Run>(`/runs/${runId}`),
  events: (after: number | null) =>
    call<{ events: AgentEvent[]; last_id: number; running: boolean }>(
      `/events?limit=500${after === null ? "" : `&after=${after}`}`,
    ),
  approvals: (status: "pending" | "all" = "all") => call<{ requests: Approval[] }>(`/approvals?status=${status}`),
  approve: (id: number, decided_by: string, note = "") =>
    call<{ new_balance: number }>(`/approvals/${id}/approve`, { method: "POST", body: JSON.stringify({ decided_by, note }) }),
  decline: (id: number, decided_by: string, note = "") =>
    call<unknown>(`/approvals/${id}/decline`, { method: "POST", body: JSON.stringify({ decided_by, note }) }),
  cash: () => call<Cash>("/cash"),
  reset: () => call<unknown>("/reset", { method: "POST" }),
};
