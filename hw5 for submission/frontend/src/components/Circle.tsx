import type { AgentEvent } from "../api";
import type { TicketRun } from "../App";
import { ORDER, SOCIETY } from "../society";

type State = "dormant" | "awake" | "done";

// What an agent is doing right now, in plain words, from its latest event.
function currently(e: AgentEvent | undefined): string {
  if (!e) return "Not called on this ticket.";
  switch (e.event) {
    case "task_received":
      return "Received a task; reading it.";
    case "model_request":
      return "Waiting for the model to think about the latest tool results.";
    case "model_response": {
      const t = e.tools.filter((x) => x.tool !== "final_result").map((x) => x.tool);
      return t.length ? `Calling ${t.join(", ")}.` : "Writing its answer.";
    }
    case "delegation_start":
      return `Handed work to another agent; waiting for its report.`;
    case "delegation_end":
      return "Got a teammate's report; continuing.";
    case "agent_output":
      return "Finished and reported back.";
    default:
      return "";
  }
}

export default function Circle({ run, running }: { run?: TicketRun; running: boolean }) {
  const byAgent = (agent: string) => (run?.events ?? []).filter((e) => e.agent === agent && e.run_id === run?.runId);

  return (
    <section className="panel circle">
      <h2>The Circle of Bones</h2>
      <p className="plain">
        The five agents. Each card shows its secret-society code name, its real job, what it's doing right now, and after
        it finishes, a short summary of what it did on this ticket. Cards stay dim if the agent wasn't needed.
      </p>

      <ul className="members">
        {ORDER.map((agent) => {
          const m = SOCIETY[agent];
          const evs = byAgent(agent);
          const last = evs[evs.length - 1];
          const outputs = evs.filter((e) => e.event === "agent_output");
          const finished = run?.finished || last?.event === "agent_output" || last?.event === "ticket_end";
          const state: State = !evs.length ? "dormant" : finished ? "done" : "awake";
          const toolsUsed = Array.from(
            new Set(evs.flatMap((e) => e.tools.map((t) => t.tool)).filter((t) => t !== "final_result")),
          );
          return (
            <li key={agent} className={`member ${state} ${state === "awake" && running ? "speaking" : ""}`} style={{ "--ink": m.color } as React.CSSProperties}>
              <div className="member-head">
                <span className="member-sigil">{m.sigil}</span>
                <div>
                  <div className="codename">{m.codename}</div>
                  <div className="rank">{m.rank}</div>
                </div>
                <span className={`state-pill ${state}`}>{state === "dormant" ? "not called" : state === "awake" ? "working" : "done"}</span>
              </div>
              <p className="job">{m.job}</p>
              <p className="why-name" title="Why this code name">
                <i>{m.meaning}</i>
              </p>

              {state !== "dormant" && (
                <div className="deeds">
                  {state === "awake" && <p className="now">Right now: {currently(last)}</p>}
                  {outputs.map((o) => (
                    <div key={o.id} className="deed">
                      <div className="deed-label">What it did{outputs.length > 1 ? ` (call ${outputs.indexOf(o) + 1})` : ""}</div>
                      <p>{o.output?.summary ?? o.said}</p>
                      {!!o.output?.actions_taken?.length && (
                        <ul>
                          {o.output.actions_taken.map((a, i) => (
                            <li key={i}>{a}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                  {toolsUsed.length > 0 && (
                    <p className="tools-used">
                      Tools used: {toolsUsed.map((t) => <code key={t}>{t}</code>)}
                    </p>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
