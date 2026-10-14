import type { Ticket } from "../api";
import type { TicketRun } from "../App";
import { STATUS_TEXT } from "../format";

// The Founder's final word on the ticket, plus the Raven's draft letter.
export default function Verdict({ ticket, run }: { ticket: Ticket | null; run?: TicketRun }) {
  const o = run?.outcome;
  if (!ticket || !run?.finished || !o) return null;

  return (
    <section className="panel verdict">
      <h2>The Founder's Verdict</h2>
      <p className="plain">
        The Boss agent's final report on ticket No. {ticket.id} when the run ended. The ticket's <i>current</i> database
        status is <code>{ticket.status}</code> ({(STATUS_TEXT[ticket.status] ?? "").split(": ")[1]}). It can change
        after the run, e.g. when you approve a payment.
      </p>
      {o.error ? (
        <p className="omen">The run stopped early: {o.error}</p>
      ) : (
        <>
          <p className="verdict-summary">{o.summary}</p>
          <p className="plain small">
            Status the Founder set at the end of the run: <code>{o.final_status}</code>
          </p>
          {!!o.needs_human?.length && (
            <>
              <h4>Still needs a human</h4>
              <ul className="needs-list">
                {o.needs_human.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </>
          )}
          {o.customer_reply_draft && (
            <div className="letter">
              <div className="letter-label">
                The Raven's draft letter to {ticket.requester}: <b>not sent</b>. A human reviews and sends it.
              </div>
              <p>{o.customer_reply_draft}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
