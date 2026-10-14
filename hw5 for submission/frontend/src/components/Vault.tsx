import { useEffect, useRef, useState } from "react";
import type { Cash } from "../api";
import { money } from "../format";

// The checking balance. When it drops (a human approved a payment), the old
// amount is struck through and the difference falls away as a coin.
export default function Vault({ cash }: { cash: Cash | null }) {
  const prev = useRef<number | null>(null);
  const [drop, setDrop] = useState<{ from: number; by: number; key: number } | null>(null);

  useEffect(() => {
    if (!cash) return;
    if (prev.current !== null && cash.balance < prev.current) {
      setDrop({ from: prev.current, by: prev.current - cash.balance, key: Date.now() });
      const t = setTimeout(() => setDrop(null), 9000);
      prev.current = cash.balance;
      return () => clearTimeout(t);
    }
    prev.current = cash.balance;
  }, [cash]);

  return (
    <div className={`vault ${drop ? "vault-drop" : ""}`} aria-live="polite">
      <div className="vault-label">The Vault</div>
      <div className="vault-balance">{cash ? money(cash.balance) : "…"}</div>
      {drop && (
        <div className="vault-change" key={drop.key}>
          <span className="coin" aria-hidden>●</span>
          <s>{money(drop.from)}</s> → paid out <b>{money(drop.by)}</b>
        </div>
      )}
      <div className="plain small">
        Checking account balance, read from the <code>cash_accounts</code> table
        {cash ? ` (as of ${cash.as_of})` : ""}. It only goes down when a human approves a payment or purchase.
      </div>
    </div>
  );
}
