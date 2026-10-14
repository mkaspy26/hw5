import { useState } from "react";
import { api, type Approval, type Cash } from "../api";
import { money } from "../format";
import { member } from "../society";

interface Props {
  approvals: Approval[];
  cash: Cash | null;
  selected: number | null;
  onDecided: () => Promise<unknown>;
}

function describe(a: Approval): string {
  if (a.kind === "rent") return `Pay rent on lease ${a.ref_id}`;
  if (a.kind === "invoice") return `Pay vendor invoice ${a.ref_id}`;
  return `Buy ${a.qty} × ${a.sku} size ${a.size} from vendor ${a.vendor_id}`;
}

// Payments and purchases the agents prepared. Nothing is paid until a human
// signs their name and presses Approve. That button calls
// POST /approvals/{id}/approve, the only thing that moves cash.
export default function Seals({ approvals, cash, selected, onDecided }: Props) {
  const [name, setName] = useState(() => localStorage.getItem("approverName") ?? "");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const pending = approvals.filter((a) => a.status === "pending");
  const decided = approvals.filter((a) => a.status !== "pending").slice(-4).reverse();

  const decide = async (a: Approval, approve: boolean) => {
    if (name.trim().length < 2) {
      setMessage({ ok: false, text: "Type your full name first. It's recorded as the person who approved or declined." });
      return;
    }
    localStorage.setItem("approverName", name.trim());
    setBusyId(a.id);
    setMessage(null);
    try {
      if (approve) {
        const r = await api.approve(a.id, name.trim());
        setMessage({ ok: true, text: `Approved #${a.id}. ${money(a.amount)} left checking; balance is now ${money(r.new_balance)}.` });
      } else {
        await api.decline(a.id, name.trim());
        setMessage({ ok: true, text: `Declined #${a.id}. Nothing was paid.` });
      }
      await onDecided();
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="panel seals">
      <h2>Seals Awaiting Your Mark</h2>
      <p className="plain">
        Payments and purchases the agents <b>prepared</b>. Agents can't spend money. Nothing leaves the checking account
        until you type your name and press <b>Approve</b>. <b>Decline</b> cancels the request and pays nothing.
      </p>

      <label className="signature">
        <span>Your name (recorded as the approver)</span>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Maxwell Kaspy" />
      </label>

      {pending.length === 0 && <p className="quiet">No seals await. When an agent prepares a payment, it appears here.</p>}

      {pending.map((a) => {
        const by = member(a.requested_by.replace(/ agent$/, ""));
        const after = cash ? cash.balance - a.amount : null;
        return (
          <article key={a.id} className={`seal ${a.ticket_id === selected ? "seal-here" : ""}`}>
            <header>
              <span className="seal-id">Request #{a.id}</span>
              <span className="seal-amount">{money(a.amount)}</span>
            </header>
            <h3>{describe(a)}</h3>
            <p className="plain small">
              For ticket {a.ticket_id} · prepared by <b style={{ color: by.color }}>{by.codename}</b> ({a.requested_by})
            </p>
            <blockquote>{a.reason}</blockquote>
            {after !== null && (
              <p className={`consequence ${after < 500 ? "grim" : ""}`}>
                If you approve: checking goes from {money(cash!.balance)} to <b>{money(after)}</b>.
                {after < 0 && " That's more than the account holds, so the backend will refuse it."}
              </p>
            )}
            <div className="seal-actions">
              <button className="approve" disabled={busyId !== null} onClick={() => decide(a, true)}>
                {busyId === a.id ? "Sealing…" : "Approve & pay"}
              </button>
              <button className="decline" disabled={busyId !== null} onClick={() => decide(a, false)}>
                Decline
              </button>
            </div>
          </article>
        );
      })}

      {message && <p className={message.ok ? "omen-good" : "omen"}>{message.text}</p>}

      {decided.length > 0 && (
        <details className="history">
          <summary>Recently decided ({decided.length})</summary>
          <ul>
            {decided.map((a) => (
              <li key={a.id}>
                #{a.id} {describe(a)}, {money(a.amount)}: <b>{a.status}</b> by {a.decided_by}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
