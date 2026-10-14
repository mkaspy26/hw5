# Campus Customs MCP Server

**What it's for:** This is the shared toolbox, and the **only** way, for every Campus Customs agent (Boss, Inventory, Accounting, Facilities, Customer Service) and the backend API to read or change shop data. Agents never open the database themselves. They call these tools, so every agent sees the same numbers and nothing gets made up. A missing row returns `{"error": ...}` instead of a guess. Write tools check their inputs against the database before changing anything.

**Database:** `data/campus_customs_new.db`, the working copy. The original `data/campus_customs.db` is never touched. Set `CC_DB_PATH` to point the server at a different copy for test runs. Read tools open the file read-only. Only write tools open it for writing.

**Built with:** [FastMCP](https://gofastmcp.com). Install with `pip install -r requirements.txt` from the project root.

**How it's started:**
- **Agent team and API:** `backend/main.py` starts it automatically over stdio, either when the API starts (`uvicorn main:app --reload --port 8000` from `backend/`) or when you run `python main.py`.
- **Claude Code:** it's registered in `hw5/.mcp.json` as `campus-customs`.
- Smoke-test evidence is in `output/mcp_smoke.json`.

## Tools (17)

| Tool | Reads / writes | Tables | Used by |
|---|---|---|---|
| `list_open_tickets()` | read | `tickets`, `desk` | Boss |
| `list_tickets()` | read | `tickets`, `desk` | Boss, API |
| `get_ticket(ticket_id)` | read | `tickets` | all 5 agents |
| `add_ticket_note(ticket_id, author, note)` | **write** (append only) | `tickets.notes`, `desk` | all 5 agents |
| `update_ticket_status(ticket_id, status, author, reason)` | **write** | `tickets.status`, `tickets.notes` | Boss |
| `check_stock_and_price(sku, size)` | read | `inventory`, `pricing` | Inventory, Customer Service |
| `get_stock_all_sizes(sku)` | read | `inventory`, `pricing` | Inventory, Customer Service |
| `list_vendors()` | read | `vendors` | Inventory |
| `quote_bulk_price(sku, qty, unit_price)` | read (math only) | `pricing` | Accounting, Customer Service |
| `get_invoice_with_vendor(invoice_id)` | read | `invoices`, `vendors`, `desk` | Inventory, Accounting |
| `get_lease_and_cash(lease_id)` | read | `leases`, `cash_accounts`, `desk` | Accounting, Facilities |
| `get_cash_position()` | read | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk` | Accounting, API |
| `list_payments()` | read | `payments` | Accounting, Facilities |
| `request_payment(kind, ref_id, amount, ticket_id, requested_by, reason, account)` | **write**, prepares only | `approval_requests`, `leases`/`invoices`, `cash_accounts`, `tickets` | Accounting |
| `request_purchase(vendor_id, sku, size, qty, ticket_id, requested_by, reason, account)` | **write**, prepares only | `approval_requests`, `vendors`, `inventory`, `pricing`, `tickets` | Inventory |
| `list_approval_requests(status)` | read | `approval_requests` | Boss, Inventory, Accounting, Facilities, API |
| `decide_approval(request_id, decision, decided_by, note)` | **write**, **moves cash** | `approval_requests`, `payments`, `cash_accounts`, `invoices`, `leases`, `tickets` | **API only** (approve/decline routes), never agents |

## How money moves

1. **Agents prepare.** `request_payment` (rent or an open invoice, exact amount owed) or `request_purchase` (restock; the amount is `qty × unit_cost` from the database) adds a **pending** row to `approval_requests` and notes it on the ticket. No cash changes.
2. **A human decides.** The dashboard calls `POST /approvals/{id}/approve` or `/decline`, which calls `decide_approval` with the person's name.
   - **Approve:** re-checks the request (amount still owed, invoice still open, enough cash, a real human name), then in one transaction:
     - inserts a `payments` row with `approved_by` = the person,
     - lowers the checking balance,
     - and either marks the invoice paid (ticket → `waiting_on_vendor`), moves the lease's `next_due` forward a month (ticket → `resolved`), or records a paid purchase invoice.
   - **Decline:** marks the request declined and notes it on the ticket. Nothing is paid.

The `approval_requests` table isn't in the original database. The server creates it on first use, including after a reset.
