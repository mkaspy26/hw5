"""Campus Customs MCP server.

The only way the agents (and the backend API) read or change shop data in
data/campus_customs_new.db. Tools return only what is in the database (or
arithmetic on it); anything missing comes back as {"error": ...}, never a
guess. Write tools validate their inputs against the database first.
Agents can only PREPARE payments/purchases; cash moves in decide_approval,
which only the human approve/decline routes call.

Set CC_DB_PATH to point the server at a different copy (used for test runs).
"""

import os
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from fastmcp import FastMCP

DB_PATH = Path(
    os.getenv("CC_DB_PATH")
    or Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"
)

# Ticket workflow states. "open" is what the seed data uses.
TICKET_STATUSES = {
    "open",
    "in_progress",
    "waiting_on_vendor",
    "waiting_on_approval",
    "waiting_on_customer",
    "resolved",
}
# Names that can never count as a human payment approver.
NON_HUMAN_APPROVERS = {
    "", "pending", "agent", "ai", "gpt", "gpt-6-luna", "model", "system", "auto",
    "boss", "inventory", "accounting", "facilities", "customer service", "customer_service",
}

mcp = FastMCP("campus-customs")


def _connect(write: bool = False) -> sqlite3.Connection:
    mode = "rw" if write else "ro"  # read tools can't change anything
    conn = sqlite3.connect(f"file:{DB_PATH}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _today(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _add_one_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return d.replace(year=year, month=month).isoformat()


def _ticket(conn: sqlite3.Connection, ticket_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()


def _append_note(conn: sqlite3.Connection, ticket_id: int, author: str, note: str) -> str:
    row = _ticket(conn, ticket_id)
    stamped = f"[{_today(conn)} · {author}] {note.strip()}"
    notes = f"{row['notes']}\n{stamped}" if row["notes"] else stamped
    conn.execute("UPDATE tickets SET notes = ? WHERE id = ?", (notes, ticket_id))
    return notes


# ---------------------------------------------------------------- tickets


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket that is not resolved yet (id, type, requester, subject,
    status, created_at), oldest first, plus the shop's desk date."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT id, type, requester, subject, status, created_at
            FROM tickets WHERE status != 'resolved' ORDER BY created_at
            """
        ).fetchall()
        return {"desk_date": _today(conn), "tickets": [dict(r) for r in rows]}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket (open or resolved) with its status and whether it is
    resolved, oldest first, plus the shop's desk date."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, status, created_at FROM tickets ORDER BY created_at"
        ).fetchall()
        tickets = [{**dict(r), "resolved": r["status"] == "resolved"} for r in rows]
        return {"desk_date": _today(conn), "tickets": tickets}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket in full: type, requester, subject, sku/size/qty, the
    lease_id or invoice_id it links to, status, notes and created_at."""
    with closing(_connect()) as conn:
        row = _ticket(conn, ticket_id)
    if row is None:
        return {"error": f"No ticket with id={ticket_id}."}
    return dict(row)


@mcp.tool
def add_ticket_note(ticket_id: int, author: str, note: str) -> dict:
    """Append a dated note to a ticket's notes (never overwrites earlier notes).
    `author` is the agent writing it, e.g. "Inventory agent". Use it to record
    findings, decisions, and DRAFT customer replies for a human to send."""
    if not note.strip():
        return {"error": "Note is empty."}
    with closing(_connect(write=True)) as conn:
        if _ticket(conn, ticket_id) is None:
            return {"error": f"No ticket with id={ticket_id}."}
        notes = _append_note(conn, ticket_id, author, note)
        conn.commit()
    return {"ticket_id": ticket_id, "notes": notes}


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, author: str, reason: str) -> dict:
    """Move a ticket to a new status and log why in its notes.

    Allowed statuses: open, in_progress, waiting_on_vendor, waiting_on_approval,
    waiting_on_customer, resolved. `reason` is required."""
    if status not in TICKET_STATUSES:
        return {"error": f"Invalid status {status!r}. Allowed: {sorted(TICKET_STATUSES)}."}
    if not reason.strip():
        return {"error": "A reason is required to change a ticket's status."}
    with closing(_connect(write=True)) as conn:
        row = _ticket(conn, ticket_id)
        if row is None:
            return {"error": f"No ticket with id={ticket_id}."}
        old = row["status"]
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        notes = _append_note(conn, ticket_id, author, f"Status {old} -> {status}: {reason}")
        conn.commit()
    return {"ticket_id": ticket_id, "old_status": old, "new_status": status, "notes": notes}


# -------------------------------------------------------------- inventory


@mcp.tool
def check_stock_and_price(sku: str, size: str) -> dict:
    """Look up how many units of one SKU + size are on hand, where they are,
    and the item's unit cost and list price.

    Use for order and discount tickets (e.g. 101 tee size S, 103 hoodies size M).
    """
    with closing(_connect()) as conn:
        row = conn.execute(
            """
            SELECT i.sku, i.name, i.size, i.qty, i.location,
                   p.unit_cost, p.list_price
            FROM inventory i
            LEFT JOIN pricing p ON p.sku = i.sku
            WHERE i.sku = ? AND i.size = ?
            """,
            (sku, size),
        ).fetchone()
    if row is None:
        return {"error": f"No inventory row for sku={sku!r}, size={size!r}."}
    return dict(row)


@mcp.tool
def get_stock_all_sizes(sku: str) -> dict:
    """Look up every size of one SKU (qty and location per size), the total on
    hand, and its unit cost and list price. Use to offer other sizes or see how
    much of a bulk order could ship now."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)
        ).fetchall()
        name = conn.execute("SELECT name FROM inventory WHERE sku = ?", (sku,)).fetchone()
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if not rows:
        return {"error": f"No inventory rows for sku={sku!r}."}
    return {
        "sku": sku,
        "name": name["name"],
        "sizes": [dict(r) for r in rows],
        "total_qty": sum(r["qty"] for r in rows),
        "unit_cost": price["unit_cost"] if price else None,
        "list_price": price["list_price"] if price else None,
    }


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with what they supply (specialty) and how many days
    they take to deliver (lead_days)."""
    with closing(_connect()) as conn:
        return {"vendors": [dict(r) for r in conn.execute("SELECT * FROM vendors ORDER BY id")]}


# ------------------------------------------------------------- accounting


@mcp.tool
def quote_bulk_price(sku: str, qty: int, unit_price: float) -> dict:
    """Check a proposed price for `qty` units of `sku` against the pricing table:
    total, discount vs list, profit per unit, and whether it falls below cost.
    Does not change anything; a human still has to approve any discount."""
    if qty <= 0 or unit_price <= 0:
        return {"error": "qty and unit_price must be positive."}
    with closing(_connect()) as conn:
        p = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if p is None:
        return {"error": f"No pricing row for sku={sku!r}."}
    return {
        "sku": sku,
        "qty": qty,
        "unit_cost": p["unit_cost"],
        "list_price": p["list_price"],
        "proposed_unit_price": unit_price,
        "discount_pct_vs_list": round(100 * (1 - unit_price / p["list_price"]), 2),
        "profit_per_unit": round(unit_price - p["unit_cost"], 2),
        "total_at_list": round(qty * p["list_price"], 2),
        "total_at_proposed": round(qty * unit_price, 2),
        "total_profit": round(qty * (unit_price - p["unit_cost"]), 2),
        "below_cost": unit_price < p["unit_cost"],
    }


@mcp.tool
def get_invoice_with_vendor(invoice_id: int) -> dict:
    """Look up one vendor invoice with its vendor's name, specialty and lead
    time, plus how many days past due it is as of the shop's desk date.

    Use when a ticket has an invoice_id (e.g. 101 is waiting on invoice 501).
    """
    with closing(_connect()) as conn:
        row = conn.execute(
            """
            SELECT inv.id AS invoice_id, inv.amount, inv.due_date, inv.status,
                   inv.description, v.id AS vendor_id, v.name AS vendor_name,
                   v.specialty, v.lead_days
            FROM invoices inv
            JOIN vendors v ON v.id = inv.vendor_id
            WHERE inv.id = ?
            """,
            (invoice_id,),
        ).fetchone()
        if row is None:
            return {"error": f"No invoice with id={invoice_id}."}
        today = _today(conn)
    result = dict(row)
    result["desk_date"] = today
    result["days_past_due"] = _days_between(row["due_date"], today)
    return result


@mcp.tool
def get_lease_and_cash(lease_id: int) -> dict:
    """Look up one lease (landlord, monthly rent, next due date) alongside
    every cash account balance, so a rent notice can be checked against
    the lease and against what the shop can actually pay.

    Use for rent tickets (e.g. 102 rent notice for lease 1).
    """
    with closing(_connect()) as conn:
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if lease is None:
            return {"error": f"No lease with id={lease_id}."}
        accounts = [dict(r) for r in conn.execute("SELECT * FROM cash_accounts")]
        today = _today(conn)
    return {
        "lease": dict(lease),
        "cash_accounts": accounts,
        "desk_date": today,
        "days_until_due": _days_between(today, lease["next_due"]),
    }


@mcp.tool
def get_cash_position() -> dict:
    """Show every cash account balance next to everything the shop owes: open
    vendor invoices and each lease's next rent payment. Returns the total owed
    and what would be left if all of it were paid."""
    with closing(_connect()) as conn:
        today = _today(conn)
        accounts = [dict(r) for r in conn.execute("SELECT * FROM cash_accounts")]
        invoices = [
            dict(r)
            for r in conn.execute(
                """
                SELECT inv.id AS invoice_id, v.name AS vendor_name, inv.amount,
                       inv.due_date, inv.description
                FROM invoices inv JOIN vendors v ON v.id = inv.vendor_id
                WHERE inv.status = 'open' ORDER BY inv.due_date
                """
            )
        ]
        leases = [
            dict(r)
            for r in conn.execute(
                "SELECT id AS lease_id, space_name, landlord, monthly_rent, next_due FROM leases"
            )
        ]
    for inv in invoices:
        inv["days_past_due"] = _days_between(inv["due_date"], today)
    for lease in leases:
        lease["days_until_due"] = _days_between(today, lease["next_due"])
    cash = sum(a["balance"] for a in accounts)
    owed = sum(i["amount"] for i in invoices) + sum(l["monthly_rent"] for l in leases)
    return {
        "desk_date": today,
        "cash_accounts": accounts,
        "total_cash": cash,
        "open_invoices": invoices,
        "upcoming_rent": leases,
        "total_owed": owed,
        "cash_left_if_all_paid": round(cash - owed, 2),
    }


@mcp.tool
def list_payments() -> dict:
    """List every payment already recorded (kind, ref_id, amount, account,
    paid_at, approved_by). Check this before paying so nothing is paid twice."""
    with closing(_connect()) as conn:
        return {"payments": [dict(r) for r in conn.execute("SELECT * FROM payments ORDER BY id")]}


# ------------------------------------------------------------- approvals
# Agents only PREPARE money moves (request_payment / request_purchase). Cash
# changes only in decide_approval, which the backend's approve/decline routes
# call after a human clicks a button. No agent is given decide_approval.

APPROVALS_SCHEMA = """
CREATE TABLE IF NOT EXISTS approval_requests (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,              -- rent | invoice | purchase
    ref_id INTEGER,                  -- lease id (rent) or invoice id (invoice)
    vendor_id INTEGER,               -- purchase only
    sku TEXT, size TEXT, qty INTEGER, -- purchase only
    amount REAL NOT NULL,
    account TEXT NOT NULL,
    ticket_id INTEGER,
    requested_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,            -- pending | approved | declined
    created_at TEXT NOT NULL,
    decided_by TEXT, decided_at TEXT, decision_note TEXT,
    payment_id INTEGER
)
"""


def _approvals_conn() -> sqlite3.Connection:
    # The original database has no approvals table; create it on first use
    # (including right after a reset).
    conn = _connect(write=True)
    conn.execute(APPROVALS_SCHEMA)
    return conn


def _payment_problem(conn: sqlite3.Connection, kind: str, ref_id: int, amount: float, account: str) -> tuple[str | None, float]:
    """Check a rent/invoice payment against the DB. Returns (error or None, amount owed)."""
    acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    if acct is None:
        return f"No cash account named {account!r}.", 0.0
    if kind == "rent":
        ref = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
        if ref is None:
            return f"No lease with id={ref_id}.", 0.0
        owed = ref["monthly_rent"]
    elif kind == "invoice":
        ref = conn.execute("SELECT * FROM invoices WHERE id = ?", (ref_id,)).fetchone()
        if ref is None:
            return f"No invoice with id={ref_id}.", 0.0
        if ref["status"] != "open":
            return f"Invoice {ref_id} is {ref['status']!r}, not open; nothing to pay.", 0.0
        owed = ref["amount"]
    else:
        return "kind must be 'rent' or 'invoice'.", 0.0
    if round(amount, 2) != round(owed, 2):
        return f"Amount {amount} does not match the {owed} owed on {kind} {ref_id}.", owed
    if acct["balance"] < owed:
        return f"Insufficient funds: {account} has {acct['balance']}, payment is {owed}.", owed
    return None, owed


def _request_row(conn: sqlite3.Connection, request_id: int) -> dict:
    return dict(conn.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone())


def _insert_request(conn: sqlite3.Connection, **fields) -> dict:
    fields.update(status="pending", created_at=_today(conn))
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    cur = conn.execute(f"INSERT INTO approval_requests ({cols}) VALUES ({marks})", tuple(fields.values()))
    if fields.get("ticket_id") and _ticket(conn, fields["ticket_id"]) is not None:
        _append_note(conn, fields["ticket_id"], fields["requested_by"],
                     f"Prepared approval request #{cur.lastrowid}: {fields['kind']} ${fields['amount']:,.2f}. Waiting for a human.")
    conn.commit()
    return _request_row(conn, cur.lastrowid)


@mcp.tool
def request_payment(kind: str, ref_id: int, amount: float, ticket_id: int, requested_by: str,
                    reason: str, account: str = "checking") -> dict:
    """PREPARE (don't make) a payment of rent or a vendor invoice for a human to approve.

    kind: "rent" (ref_id = lease id) or "invoice" (ref_id = invoice id). amount
    must exactly equal what's owed. Creates a pending approval request and notes
    it on the ticket. No money moves until a human approves it on the dashboard.
    If an identical request is already pending, returns that one instead."""
    with closing(_approvals_conn()) as conn:
        problem, owed = _payment_problem(conn, kind, ref_id, amount, account)
        if problem:
            return {"error": problem}
        existing = conn.execute(
            "SELECT id FROM approval_requests WHERE kind = ? AND ref_id = ? AND status = 'pending'",
            (kind, ref_id),
        ).fetchone()
        if existing:
            return {"already_pending": True, "request": _request_row(conn, existing["id"])}
        request = _insert_request(conn, kind=kind, ref_id=ref_id, amount=owed, account=account,
                                  ticket_id=ticket_id, requested_by=requested_by, reason=reason)
    return {"request": request, "note": "Pending human approval. Nothing has been paid."}


@mcp.tool
def request_purchase(vendor_id: int, sku: str, size: str, qty: int, ticket_id: int,
                     requested_by: str, reason: str, account: str = "checking") -> dict:
    """PREPARE (don't make) a restock purchase from a vendor for a human to approve.

    The amount is computed from the database (qty x pricing.unit_cost), not
    chosen by the agent. Returns the estimated arrival (desk date + vendor
    lead_days after approval). No money moves until a human approves it."""
    if qty <= 0:
        return {"error": "qty must be positive."}
    with closing(_approvals_conn()) as conn:
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"error": f"No vendor with id={vendor_id}."}
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return {"error": f"No inventory row for sku={sku!r}, size={size!r}."}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"error": f"No pricing row for sku={sku!r}; can't cost the purchase."}
        existing = conn.execute(
            """SELECT id FROM approval_requests WHERE kind = 'purchase' AND sku = ? AND size = ?
               AND status = 'pending'""", (sku, size),
        ).fetchone()
        if existing:
            return {"already_pending": True, "request": _request_row(conn, existing["id"])}
        amount = round(qty * price["unit_cost"], 2)
        request = _insert_request(conn, kind="purchase", vendor_id=vendor_id, sku=sku, size=size, qty=qty,
                                  amount=amount, account=account, ticket_id=ticket_id,
                                  requested_by=requested_by, reason=reason)
    return {
        "request": request,
        "vendor": dict(vendor),
        "amount_basis": f"{qty} x unit_cost {price['unit_cost']}",
        "note": f"Pending human approval. If approved, arrives about {vendor['lead_days']} days later.",
    }


@mcp.tool
def list_approval_requests(status: str = "pending") -> dict:
    """List approval requests (prepared payments and purchases) by status:
    pending, approved, declined, or all. Check this before preparing a new one."""
    with closing(_approvals_conn()) as conn:
        if status == "all":
            rows = conn.execute("SELECT * FROM approval_requests ORDER BY id").fetchall()
        else:
            rows = conn.execute("SELECT * FROM approval_requests WHERE status = ? ORDER BY id", (status,)).fetchall()
        return {"requests": [dict(r) for r in rows]}


@mcp.tool
def decide_approval(request_id: int, decision: str, decided_by: str, note: str = "") -> dict:
    """HUMAN-ONLY (called by the dashboard's approve/decline routes, never by agents).

    decision "approve": re-checks the request against the database, then moves
    the money in one transaction: inserts a payments row, lowers the cash
    balance, and marks the invoice paid / moves the lease due date / records the
    purchase invoice. decision "decline": marks it declined; nothing is paid."""
    if decided_by.strip().lower() in NON_HUMAN_APPROVERS:
        return {"error": "decided_by must be a named human."}
    if decision not in ("approve", "decline"):
        return {"error": "decision must be 'approve' or 'decline'."}
    with closing(_approvals_conn()) as conn:
        req = conn.execute("SELECT * FROM approval_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"error": f"No approval request with id={request_id}."}
        if req["status"] != "pending":
            return {"error": f"Request {request_id} is already {req['status']}."}
        today = _today(conn)
        who = decided_by.strip()

        if decision == "decline":
            conn.execute(
                "UPDATE approval_requests SET status='declined', decided_by=?, decided_at=?, decision_note=? WHERE id=?",
                (who, today, note, request_id),
            )
            if req["ticket_id"] and _ticket(conn, req["ticket_id"]) is not None:
                _append_note(conn, req["ticket_id"], f"{who} (human)",
                             f"DECLINED request #{request_id} ({req['kind']} ${req['amount']:,.2f}). {note}".strip())
            conn.commit()
            return {"request": _request_row(conn, request_id), "paid": False}

        # approve: re-validate now, since cash or the bill may have changed
        if req["kind"] == "purchase":
            acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (req["account"],)).fetchone()
            problem = None if acct and acct["balance"] >= req["amount"] else "Insufficient funds for this purchase."
        else:
            problem, _ = _payment_problem(conn, req["kind"], req["ref_id"], req["amount"], req["account"])
        if problem:
            return {"error": f"Can't approve request {request_id}: {problem}"}

        ticket_status = None
        if req["kind"] == "purchase":
            vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (req["vendor_id"],)).fetchone()
            cur = conn.execute(
                "INSERT INTO invoices (vendor_id, amount, due_date, status, description) VALUES (?, ?, ?, 'paid', ?)",
                (req["vendor_id"], req["amount"], today,
                 f"Restock purchase {req['qty']} x {req['sku']} {req['size']} (request #{request_id})"),
            )
            pay_kind, pay_ref = "purchase", cur.lastrowid
            summary = (f"APPROVED request #{request_id}: bought {req['qty']} x {req['sku']} {req['size']} from "
                       f"{vendor['name']} for ${req['amount']:,.2f}; arrives in about {vendor['lead_days']} days.")
        else:
            pay_kind, pay_ref = req["kind"], req["ref_id"]
            if req["kind"] == "rent":
                lease = conn.execute("SELECT * FROM leases WHERE id = ?", (pay_ref,)).fetchone()
                conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (_add_one_month(lease["next_due"]), pay_ref))
                ticket_status = "resolved"
            else:
                conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (pay_ref,))
                ticket_status = "waiting_on_vendor"
            summary = f"APPROVED request #{request_id}: paid {req['kind']} {pay_ref} ${req['amount']:,.2f}."

        acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (req["account"],)).fetchone()
        new_balance = round(acct["balance"] - req["amount"], 2)
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (new_balance, today, req["account"]))
        pay = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (pay_kind, pay_ref, req["amount"], req["account"], today, who),
        )
        conn.execute(
            """UPDATE approval_requests SET status='approved', decided_by=?, decided_at=?, decision_note=?,
               payment_id=? WHERE id=?""",
            (who, today, note, pay.lastrowid, request_id),
        )
        tid = req["ticket_id"]
        if tid and _ticket(conn, tid) is not None:
            _append_note(conn, tid, f"{who} (human)", f"{summary} Checking now ${new_balance:,.2f}.")
            if ticket_status:
                old = _ticket(conn, tid)["status"]
                conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (ticket_status, tid))
                _append_note(conn, tid, f"{who} (human)", f"Status {old} -> {ticket_status}: payment approved.")
        conn.commit()
        payment = dict(conn.execute("SELECT * FROM payments WHERE id = ?", (pay.lastrowid,)).fetchone())
        return {"request": _request_row(conn, request_id), "paid": True, "payment": payment,
                "new_balance": new_balance, "ticket_status": ticket_status}


if __name__ == "__main__":
    mcp.run(show_banner=False)
