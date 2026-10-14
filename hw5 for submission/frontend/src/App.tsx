import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type AgentEvent, type Approval, type Cash, type Run, type Ticket } from "./api";
import Vault from "./components/Vault";
import Petitions from "./components/Petitions";
import Seance from "./components/Seance";
import Circle from "./components/Circle";
import Seals from "./components/Seals";
import Verdict from "./components/Verdict";

export interface TicketRun {
  runId: string;
  finished: boolean;
  outcome?: AgentEvent["output"];
  events: AgentEvent[]; // agent events of this run + human decisions on this ticket after it started
}

// Group the audit trail into "the latest run" per ticket.
function latestRuns(events: AgentEvent[]): Record<number, TicketRun> {
  let byTicket: Record<number, TicketRun> = {};
  for (const e of events) {
    if (e.event === "db_reset") byTicket = {}; // a reset puts every ticket back to "never run"
    if (e.ticket_id === null) continue;
    if (e.event === "ticket_start") byTicket[e.ticket_id] = { runId: e.run_id, finished: false, events: [] };
    const run = byTicket[e.ticket_id];
    if (!run) continue;
    if (e.run_id === run.runId || e.run_id === "api") run.events.push(e);
    if (e.event === "ticket_end" && e.run_id === run.runId) {
      run.finished = true;
      run.outcome = e.output;
    }
  }
  return byTicket;
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [cash, setCash] = useState<Cash | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  // ?ticket=102 in the URL opens the board on that ticket (handy for sharing and screenshots).
  const [selected, setSelected] = useState<number | null>(() => {
    const t = Number(new URLSearchParams(location.search).get("ticket"));
    return Number.isInteger(t) && t > 0 ? t : null;
  });
  useEffect(() => {
    if (selected !== null) history.replaceState(null, "", `?ticket=${selected}`);
  }, [selected]);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [backendBusy, setBackendBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastId = useRef<number | null>(null);

  const refreshShop = useCallback(async () => {
    try {
      const [t, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals("all")]);
      setTickets(t.tickets);
      setCash(c);
      setApprovals(a.requests);
      setError(null);
      setSelected((s) => s ?? t.tickets[0]?.id ?? null);
    } catch (err) {
      setError(`Can't reach the backend at http://localhost:8000 (${(err as Error).message}). Is uvicorn running?`);
    }
  }, []);

  const refreshEvents = useCallback(async () => {
    try {
      const res = await api.events(lastId.current);
      // The audit file only grows; if it got shorter, start over.
      if (lastId.current !== null && res.last_id < lastId.current) {
        lastId.current = null;
        setEvents([]);
        return;
      }
      if (res.events.length) setEvents((prev) => [...prev, ...res.events]);
      lastId.current = res.last_id;
      setBackendBusy(res.running);
    } catch {
      /* refreshShop reports connection problems */
    }
  }, []);

  // Poll faster while the agents are working.
  const working = backendBusy || activeRun?.status === "running";
  useEffect(() => {
    refreshShop();
    refreshEvents();
  }, [refreshShop, refreshEvents]);
  useEffect(() => {
    const ev = setInterval(refreshEvents, working ? 1500 : 5000);
    const shop = setInterval(refreshShop, working ? 3000 : 10000);
    return () => {
      clearInterval(ev);
      clearInterval(shop);
    };
  }, [working, refreshEvents, refreshShop]);

  // Follow the run we started until it finishes.
  useEffect(() => {
    if (!activeRun || activeRun.status !== "running") return;
    const t = setInterval(async () => {
      try {
        const r = await api.run(activeRun.run_id);
        if (r.status !== "running") {
          setActiveRun(r);
          await Promise.all([refreshEvents(), refreshShop()]);
        }
      } catch (err) {
        setError((err as Error).message);
      }
    }, 2000);
    return () => clearInterval(t);
  }, [activeRun, refreshEvents, refreshShop]);

  const runs = useMemo(() => latestRuns(events), [events]);
  const ticket = tickets.find((t) => t.id === selected) ?? null;
  const run = selected !== null ? runs[selected] : undefined;
  const runningTicketId = activeRun?.status === "running" ? activeRun.ticket_id : null;

  const summon = async (id: number) => {
    setError(null);
    try {
      setSelected(id);
      setActiveRun(await api.runTicket(id));
      setBackendBusy(true);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const reset = async () => {
    if (!confirm("Reset the database to its original values?\n\nAll 3 tickets go back to open, checking goes back to $3,400.00, and prepared payments are erased. The audit log is kept.")) return;
    try {
      await api.reset();
      setActiveRun(null);
      await Promise.all([refreshShop(), refreshEvents()]);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="tomb">
      <div className="fog" aria-hidden />
      <header className="masthead">
        <div className="crest" aria-hidden>
          <span className="skull">☠</span>
          <span className="numeral">322</span>
        </div>
        <div className="titles">
          <h1>The Tomb</h1>
          <p className="motto">What is spoken in the Tomb stays in the Tomb.</p>
          <p className="plain">
            Campus Customs back office. Five AI agents (model <code>gpt-6-luna</code>) work the shop's support tickets.
            You pick a ticket, watch them work, and approve any payment they prepare.
          </p>
        </div>
        <Vault cash={cash} />
      </header>

      {error && (
        <div className="omen" role="alert">
          <b>Something went wrong:</b> {error}
        </div>
      )}

      <main className="chambers">
        <aside className="left">
          <Petitions
            tickets={tickets}
            runs={runs}
            selected={selected}
            onSelect={setSelected}
            onSummon={summon}
            busy={working}
            runningTicketId={runningTicketId}
            approvals={approvals}
          />
          <Seals approvals={approvals} cash={cash} selected={selected} onDecided={() => Promise.all([refreshShop(), refreshEvents()])} />
        </aside>

        <section className="center">
          <Seance ticket={ticket} run={run} running={runningTicketId === selected && runningTicketId !== null} />
        </section>

        <aside className="right">
          <Circle run={run} running={runningTicketId === selected && runningTicketId !== null} />
          <Verdict ticket={ticket} run={run} />
        </aside>
      </main>

      <footer className="crypt-floor">
        <button className="ghost" onClick={reset} disabled={working}>
          ⟲ Turn back the night
        </button>
        <span className="plain small">
          Resets the database to its original values: tickets open, checking at $3,400.00, no prepared payments. The
          audit log (<code>output/audit_trail.json</code>) is never erased.
        </span>
      </footer>
    </div>
  );
}
