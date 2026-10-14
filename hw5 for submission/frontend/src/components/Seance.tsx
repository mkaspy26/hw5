import { useEffect, useRef } from "react";
import type { AgentEvent, Ticket } from "../api";
import type { TicketRun } from "../App";
import { args, money, pretty } from "../format";
import { member } from "../society";

// One line in the live log, written in the speaking agent's ink.
function Line({ e }: { e: AgentEvent }) {
  const m = member(e.agent);
  const who = (
    <span className="who" style={{ color: m.color }}>
      <span className="sigil">{m.sigil}</span> {m.codename}
    </span>
  );
  const ink = { "--ink": m.color } as React.CSSProperties;

  switch (e.event) {
    case "task_received":
      return (
        <li className="line summon-line" style={ink}>
          {who} <span className="verb">was summoned</span> ({e.agent} agent) with this task:
          <blockquote>{e.said?.replace(/^Received task: /, "")}</blockquote>
        </li>
      );
    case "model_response": {
      const tools = e.tools.filter((t) => t.tool !== "delegate");
      if (!e.said && tools.length === 0) return null;
      return (
        <li className="line" style={ink}>
          {who} {e.said && <span className="speech">“{e.said}”</span>}
          {tools.map((t, i) => (
            <div key={i} className="incantation">
              <span className="verb">calls tool</span> <code>{t.tool}({args(t.args)})</code>
            </div>
          ))}
        </li>
      );
    }
    case "model_request":
      return (
        <li className="line result-line" style={ink}>
          {e.tool_results.filter((r) => r.tool !== "delegate").map((r, i) => (
            <details key={i}>
              <summary>
                <span className="verb">Result of</span> <code>{r.tool}</code> returned to {m.codename}
              </summary>
              <pre>{pretty(r.result)}</pre>
            </details>
          ))}
        </li>
      );
    case "delegation_start": {
      const to = e.said?.match(/^Asked ([^:]+): ([\s\S]*)$/);
      const target = member(to?.[1] ?? "");
      return (
        <li className="line handoff" style={ink}>
          {who} <span className="verb">passes the candle to</span>{" "}
          <span className="who" style={{ color: target.color }}>
            {target.sigil} {target.codename}
          </span>{" "}
          ({to?.[1]} agent):
          <blockquote>{to?.[2]}</blockquote>
        </li>
      );
    }
    case "delegation_end":
      return (
        <li className="line handoff-back" style={ink}>
          {who} <span className="verb">received a report</span>: <span className="speech">{e.said?.replace(/^(.+?) reported: /, "")}</span>
        </li>
      );
    case "delegation_refused":
      return (
        <li className="line warn" style={ink}>
          {who} <span className="verb">tried to hand off work but was stopped</span> (a safety limit): {e.said}
        </li>
      );
    case "agent_output":
      return (
        <li className="line finished" style={ink}>
          {who} <span className="verb">finished and reported</span>: <span className="speech">{e.said}</span>
        </li>
      );
    case "ticket_end":
      return (
        <li className="line rite-end">
          ☠ <b>The rite is complete.</b> The Founder's final status for this ticket:{" "}
          <code>{e.output?.final_status ?? "error"}</code>
          {e.output?.error && <> (stopped: {e.output.error})</>}
        </li>
      );
    case "human_decision": {
      const o = e.output as
        | { decision?: string; decided_by?: string; new_balance?: number | null; request?: { id: number; kind: string; amount: number } }
        | undefined;
      const approved = o?.decision === "approve";
      return (
        <li className="line human">
          ✍ <b>{o?.decided_by}</b> (a human, not an agent) {approved ? "approved" : "declined"} request #{o?.request?.id}:{" "}
          {o?.request?.kind} payment of {money(o?.request?.amount)}.{" "}
          {approved && o?.new_balance != null ? <>The money left checking, which is now {money(o.new_balance)}.</> : <>Nothing was paid.</>}
        </li>
      );
    }
    case "money_request_blocked":
    case "stopped_by_limit":
      return <li className="line warn">⚠ Safety limit reached: {e.said}</li>;
    default:
      return null;
  }
}

export default function Seance({ ticket, run, running }: { ticket: Ticket | null; run?: TicketRun; running: boolean }) {
  const end = useRef<HTMLDivElement>(null);
  const count = run?.events.length ?? 0;
  useEffect(() => {
    if (running) end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [count, running]);

  return (
    <section className="panel seance">
      <h2>The Séance</h2>
      <p className="plain">
        A live log of {ticket ? <>ticket <b>No. {ticket.id}</b></> : "the chosen ticket"}: every task an agent receives,
        every tool it calls on the shop's database (and what came back), and every handoff between agents. Each agent
        writes in its own color. While the agents work, this updates every 1.5 seconds.
      </p>

      {!run && (
        <div className="empty-altar">
          <div className="candles" aria-hidden>
            <span>🕯</span>
            <span>🕯</span>
            <span>🕯</span>
          </div>
          <p>The candles are unlit. No run has happened on this ticket since the last reset.</p>
          <p className="plain small">Press <b>Summon the Society</b> on the ticket to start the agent team.</p>
        </div>
      )}

      {run && (
        <ol className="transcript">
          {run.events.map((e) => (
            <Line key={e.id} e={e} />
          ))}
          {running && (
            <li className="line thinking">
              <span className="flicker">The society is deliberating… (waiting for the model's next reply)</span>
            </li>
          )}
        </ol>
      )}
      <div ref={end} />
    </section>
  );
}
