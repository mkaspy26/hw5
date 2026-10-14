import type { Approval, Ticket } from "../api";
import type { TicketRun } from "../App";
import { STATUS_TEXT, TICKET_TYPE } from "../format";

interface Props {
  tickets: Ticket[];
  runs: Record<number, TicketRun>;
  selected: number | null;
  onSelect: (id: number) => void;
  onSummon: (id: number) => void;
  busy: boolean;
  runningTicketId: number | null;
  approvals: Approval[];
}

// The ticket list. Each ticket is a sealed petition: the wax seal is whole
// until the agent team finishes a run on it, then it's broken and stamped
// "Resolved by the Society".
export default function Petitions({ tickets, runs, selected, onSelect, onSummon, busy, runningTicketId, approvals }: Props) {
  return (
    <section className="panel">
      <h2>Petitions to the Society</h2>
      <p className="plain">
        The shop's {tickets.length || 3} support tickets. Click one to view it, then press <b>Summon the Society</b> to
        run the five AI agents on it (takes about a minute; uses roughly 45–70k tokens on the Portkey account).
      </p>

      <ol className="petitions">
        {tickets.map((t) => {
          const run = runs[t.id];
          const running = runningTicketId === t.id;
          const finished = !!run?.finished;
          const pending = approvals.filter((a) => a.ticket_id === t.id && a.status === "pending").length;
          return (
            <li key={t.id}>
              <article
                className={`petition ${selected === t.id ? "chosen" : ""} ${finished ? "sealed-broken" : ""} ${running ? "in-rite" : ""}`}
                onClick={() => onSelect(t.id)}
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && onSelect(t.id)}
              >
                <div className="wax" aria-hidden>{finished ? "✓" : "☠"}</div>
                <header>
                  <span className="petition-no">No. {t.id}</span>
                  <span className="petition-type">{TICKET_TYPE[t.type] ?? t.type}</span>
                </header>
                <h3>{t.subject}</h3>
                <p className="petitioner">from {t.requester}</p>

                {finished && <div className="stamp">Resolved by the Society</div>}

                <dl className="facts">
                  <dt>Run</dt>
                  <dd>
                    {running ? (
                      <span className="flicker">The agents are working on it now…</span>
                    ) : finished ? (
                      "The agent team finished its run on this ticket."
                    ) : (
                      "Not run yet."
                    )}
                  </dd>
                  <dt>Database status</dt>
                  <dd>
                    <code>{t.status}</code>: {(STATUS_TEXT[t.status] ?? t.status).split(": ")[1]}
                  </dd>
                  {pending > 0 && (
                    <>
                      <dt>Needs you</dt>
                      <dd className="needs">
                        {pending} payment/purchase waiting for approval (see <i>Seals Awaiting Your Mark</i>).
                      </dd>
                    </>
                  )}
                </dl>

                <button
                  className="summon"
                  disabled={busy}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSummon(t.id);
                  }}
                  title={busy ? "The team works one ticket at a time; wait for the current run to finish." : ""}
                >
                  {running ? "Rite in progress…" : finished ? "Summon again" : "Summon the Society"}
                </button>
              </article>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
