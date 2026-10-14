# Campus Customs Agent Harness

The single reference for the Campus Customs agent system (hw5): the data, the MCP tools, the 5 agents, the API, the dashboard, the safety rules, and the results of the real run.

**Contents**
1. Data and tables: the 9 original tables plus `approval_requests`
2. Open tickets and how they link
3. Agent team (5 agents, code names, delegation)
4. MCP tools (current: 17)
5. Backend API routes
6. Audit trail
7. Safety rules and token limits
8. Dashboard
9. Final run results (Problem 9)

The "MCP Tools (`mcp_server/server.py`)" section right after the tickets is the original Problem 3 write-up of the first 3 tools. The full current list is in section 4.

## Data

- **Original (read-only reference):** `data/campus_customs.db`
- **Working copy (agents read and write here):** `data/campus_customs_new.db`
- **"Today" for the agents:** `desk.date_today` = **2026-08-31**
- **Reset:** `POST /reset` (or the dashboard's "Turn back the night") copies the original over the working copy. The audit trail is never reset.

## Tables

### `desk` (1 row)
| Field | Type | Notes |
|---|---|---|
| `date_today` | TEXT | Current business date (2026-08-31) |
| `notes` | TEXT | Free-form desk notes (empty) |

**Why it matters:** Gives agents the date to use for "today", so they can tell what is due or overdue without relying on the system clock.

### `inventory` (10 rows, PK = `sku` + `size`)
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT | Product code, e.g. `CC-TEE-WHITE` |
| `name` | TEXT | Product name |
| `size` | TEXT | S / M / L / XL, or OS (one size) |
| `qty` | INTEGER | Units on hand |
| `location` | TEXT | Aisle in the shop |

**Why it matters:** Agents check this first to see whether an order can be filled now. Tee size S and the Crest Mug both have 0 units.

### `pricing` (4 rows)
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT PK | Links to `inventory.sku` |
| `unit_cost` | REAL | What the shop pays per unit |
| `list_price` | REAL | Normal selling price |

**Why it matters:** Agents quote prices from here. Discount requests can't go below `unit_cost` without losing money.

### `vendors` (3 rows)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Referenced by `invoices.vendor_id` |
| `name` | TEXT | Bulldog Print Co / Elm City Gifts / QuickShip CT |
| `specialty` | TEXT | Apparel reprint / mugs and small goods / local courier |
| `lead_days` | INTEGER | Days to deliver (5 / 3 / 1) |

**Why it matters:** Tells agents who can restock an item and how long it takes, so they give customers realistic dates.

### `leases` (1 row)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Referenced by `tickets.lease_id` |
| `space_name` | TEXT | Chapel Street shop |
| `landlord` | TEXT | Elm City Properties |
| `monthly_rent` | REAL | $2,400 |
| `next_due` | TEXT | 2026-09-02 |
| `notes` | TEXT | (empty) |

**Why it matters:** Rent is the shop's biggest fixed bill. Agents use this table to check that a rent notice is real and that the amount is right.

### `cash_accounts` (1 row)
| Field | Type | Notes |
|---|---|---|
| `name` | TEXT PK | `checking` |
| `balance` | REAL | $3,400 |
| `date` | TEXT | Date of the balance (2026-08-31) |

**Why it matters:** Caps what the shop can pay. Every payment has to fit within this balance.

### `payments` (0 rows)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `kind` | TEXT | What was paid, e.g. rent or invoice |
| `ref_id` | INTEGER | ID of the lease or invoice being paid |
| `amount` | REAL | |
| `account` | TEXT | Links to `cash_accounts.name` |
| `paid_at` | TEXT | Timestamp |
| `approved_by` | TEXT | Who approved the payment |

**Why it matters:** This is where every payment is recorded, and the shop reads it to see what has already been paid. The required `approved_by` field means a named person must approve each payment, so an agent can't move money on its own.

### `invoices` (1 row)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Referenced by `tickets.invoice_id` |
| `vendor_id` | INTEGER FK → `vendors.id` | |
| `amount` | REAL | |
| `due_date` | TEXT | |
| `status` | TEXT | `open` / (presumably) `paid` |
| `description` | TEXT | |

**Why it matters:** Lists what the shop owes vendors. Agents need it to see which bills are blocking restocks and which are overdue.

### `tickets` (3 rows, all `open` in the original)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `type` | TEXT | `customer_order` / `rent_notice` / `price_override` |
| `requester` | TEXT | Who asked |
| `subject` | TEXT | Short title |
| `sku`, `size`, `qty` | TEXT / TEXT / INTEGER | Item requested → `inventory` / `pricing` |
| `lease_id` | INTEGER FK → `leases.id` | Set for rent tickets |
| `invoice_id` | INTEGER FK → `invoices.id` | Set when a ticket depends on a vendor bill |
| `status` | TEXT | `open` |
| `notes` | TEXT | Requester's message |
| `created_at` | TEXT | ISO timestamp |

**Why it matters:** These are the jobs the agents have to handle. Each ticket's foreign keys tell an agent which other tables to look up.

### `approval_requests` (added in Problem 7; not in the original DB, created on first use)
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Request number shown on the dashboard ("Request #1") |
| `kind` | TEXT | `rent` / `invoice` / `purchase` |
| `ref_id` | INTEGER | Lease id (rent) or invoice id (invoice) |
| `vendor_id`, `sku`, `size`, `qty` | | Purchases only |
| `amount` | REAL | Exact amount owed (rent/invoice) or `qty × unit_cost` (purchase), computed by the server |
| `account` | TEXT | `checking` |
| `ticket_id` | INTEGER | Ticket the request belongs to (set by the guard, not the agent) |
| `requested_by` | TEXT | Agent that prepared it (set by the guard) |
| `reason` | TEXT | The agent's one-line justification with numbers |
| `status` | TEXT | `pending` → `approved` / `declined` |
| `created_at`, `decided_by`, `decided_at`, `decision_note` | TEXT | Who decided and when (desk date) |
| `payment_id` | INTEGER | Links to the `payments` row created on approval |

**Why it matters:** This is the queue between "an agent thinks we should pay" and "money actually moves". Agents can only add `pending` rows. Only a human click (`decide_approval` via the API) turns one into a payment.

## Open Tickets and How They Link

| Ticket | What it asks | Linked rows | What the data shows |
|---|---|---|---|
| **101** customer_order (Tauhid Zaman) | 1 × Classic Bulldog Tee, size S | `inventory` CC-TEE-WHITE/S → **qty 0**; `invoices` 501 → vendor 1 Bulldog Print Co | Out of stock. A $840 rush reprint of exactly this item is on invoice 501, which is still **open and overdue** (due 08-28). Bulldog Print Co needs 5 days, so if the reprint isn't already done the tee arrives around 09-05 at the earliest. |
| **102** rent_notice (Elm City Properties) | Pay shop rent | `leases` 1 → $2,400 due **2026-09-02** | The amount and date match the lease, so the notice is consistent. Paying it means writing a row to `payments`, which needs `approved_by`. |
| **103** price_override (Yale AI Club) | 20 hoodies, size M, bulk discount | `inventory` CC-HOOD-NAVY/M → **qty 8**; `pricing` → cost $22, list $58 | Only 8 of the 20 are in stock, so 12 more need a reprint (Bulldog Print Co, 5 days). Full price is $1,160. Any discount has to stay above the $22 unit cost and needs human sign-off. |

**Cash check:** checking holds $3,400. Rent ($2,400) plus invoice 501 ($840) comes to $3,240, which leaves only **$160**. Paying both is possible but leaves almost nothing for a hoodie reprint, so agents should flag cash before approving payments.

**Other notes for later problems**
- There is no customers/users table. Requesters exist only as names on `tickets`.
- No status values appear yet besides `open`, so the allowed values (e.g. `paid`, `closed`) still need to be decided.
- Agents should write only to `campus_customs_new.db` and never modify the original.

## MCP Tools (`mcp_server/server.py`): original 3 tools from Problem 3 (full current list in "MCP Tools (current: 17)" below)

*(Problem 3 snapshot)* These first tools are read-only against `data/campus_customs_new.db` and return only database values. A missing row returns `{"error": ...}`. The date math (days past due / until due) uses `desk.date_today`, not the system clock.

### 1. `check_stock_and_price(sku, size)`
- **Reads:** `inventory` (qty, location for that exact sku + size) joined to `pricing` (unit_cost, list_price)
- **Unlocks:** **Ticket 103** (also used by 101)
- **Why it's the right tool:** Ticket 103 asks for 20 × CC-HOOD-NAVY size M at a discount. This one call shows only **8** are on hand (so 12 are short) and shows the **$22 cost vs. $58 list**, which is the floor and the ceiling for any bulk price. For 101 it confirms the tee in size S is at **0**.

### 2. `get_invoice_with_vendor(invoice_id)`
- **Reads:** `invoices` (amount, due_date, status, description) joined to `vendors` (name, specialty, lead_days), plus `desk` for today's date
- **Unlocks:** **Ticket 101**
- **Why it's the right tool:** Ticket 101 has no tee to sell but carries `invoice_id = 501`. This tool shows that invoice is the **$840 Bulldog Print Co rush reprint of that exact tee**, still **open and 3 days overdue**, with a **5-day lead time**. That's what the agent needs to tell Tauhid when the tee can actually arrive.

### 3. `get_lease_and_cash(lease_id)`
- **Reads:** `leases` (landlord, monthly_rent, next_due) plus all of `cash_accounts` (balance), plus `desk` for today's date
- **Unlocks:** **Ticket 102**
- **Why it's the right tool:** Ticket 102 is an email claiming rent is due. Comparing it against **lease 1 ($2,400 to Elm City Properties, due 09-02, 2 days away)** and the **$3,400 checking balance** in one call lets the agent check the notice is real and that the shop can pay it before asking a human to approve.

**Next tool likely needed:** `get_ticket(ticket_id)`, so agents can read a ticket's sku / size / lease_id / invoice_id themselves instead of being handed them.

---

## Agent Team (`backend/`, PydanticAI)

All 5 agents run **`gpt-6-luna`** through Portkey (`PORTKEY_API_KEY`). Each agent's prompt is in `backend/prompts/<agent>.md`. Its definition (role, allowed MCP tools, output type) and the shared data types are in `backend/models.py` (`SPECS`). The team, audit trail, limits and API are in `backend/main.py`.

**Run it**, from `hw5/backend/` with `source ../.venv/bin/activate`:
- **API (for the dashboard):** `uvicorn main:app --reload --port 8000`
- **Terminal only:** `python main.py [--ticket N]`

| Agent | Job | MCP tools it may call | Returns |
|---|---|---|---|
| **Boss** | Triages each ticket, delegates, sets the ticket status, signs off. The only agent that changes status. | `list_open_tickets`, `list_tickets`, `get_ticket`, `update_ticket_status`, `add_ticket_note`, `list_approval_requests` | `TicketOutcome` |
| **Inventory** | Stock per size, alternatives, restock vendor and lead time. **Prepares** restock purchases. | `get_ticket`, `check_stock_and_price`, `get_stock_all_sizes`, `list_vendors`, `get_invoice_with_vendor`, `request_purchase`, `list_approval_requests`, `add_ticket_note` | `SpecialistReport` |
| **Accounting** | Cash position, invoices, discount math. **Prepares** rent and invoice payments. | `get_ticket`, `get_invoice_with_vendor`, `get_lease_and_cash`, `get_cash_position`, `list_payments`, `quote_bulk_price`, `request_payment`, `list_approval_requests`, `add_ticket_note` | `SpecialistReport` |
| **Facilities** | Verifies rent notices against the lease, checks rent isn't already paid or prepared, hands verified rent to Accounting. | `get_ticket`, `get_lease_and_cash`, `list_payments`, `list_approval_requests`, `add_ticket_note` | `SpecialistReport` |
| **Customer Service** | Drafts every reply to a requester, using only tool facts. A human sends it. | `get_ticket`, `check_stock_and_price`, `get_stock_all_sizes`, `quote_bulk_price`, `add_ticket_note` | `SpecialistReport` |

**Delegation (full connectivity).** Every agent has a `delegate(to, task)` tool that can reach any other agent. The sub-agent runs its own loop and returns its report.

**Agent loop.** Each agent runs `model → tool calls → model → …` until it returns its typed output (`Agent.iter` in `backend/main.py`).

**Ticket flow:** `team.handle_ticket` hands the ticket to the Boss. The Boss delegates to fact-finders first and Customer Service last. Money moves are only **prepared** as approval requests. The Boss then sets the status and returns a `TicketOutcome`.

## MCP Tools (current: 17)

All 17 run over `data/campus_customs_new.db`.
- **Problem 3:** `check_stock_and_price`, `get_invoice_with_vendor`, `get_lease_and_cash`.
- **Problem 5:** the ticket, stock, vendor, pricing, cash and payment tools.
- **Problem 7:** `list_tickets` and the 4 approval tools. `record_payment` (Problem 5), which agents could call, was replaced by prepare → human approve.

| Tool | Tables | R/W | Used by | Unlocks |
|---|---|---|---|---|
| `check_stock_and_price` | `inventory`, `pricing` | R | Inventory, Customer Service | 101 (tee S = 0), 103 (hoodie M = 8; $22 cost / $58 list) |
| `get_invoice_with_vendor` | `invoices`, `vendors`, `desk` | R | Inventory, Accounting | 101 (invoice 501: $840, open, 3 days overdue, 5-day lead) |
| `get_lease_and_cash` | `leases`, `cash_accounts`, `desk` | R | Accounting, Facilities | 102 (rent $2,400 due 09-02; $3,400 checking) |
| `list_open_tickets` | `tickets`, `desk` | R | Boss | All: find the work |
| `list_tickets` | `tickets`, `desk` | R | Boss, API `GET /tickets` | All: open vs. resolved board |
| `get_ticket` | `tickets` | R | all 5 | All: sku/size/qty, lease_id/invoice_id |
| `get_stock_all_sizes` | `inventory`, `pricing` | R | Inventory, Customer Service | 101 (offer M/L/XL), 103 (32 across sizes) |
| `list_vendors` | `vendors` | R | Inventory | 103 (who can reprint the 12 missing, how fast) |
| `quote_bulk_price` | `pricing` | R | Accounting, Customer Service | 103 (discount totals, profit, below-cost flag) |
| `get_cash_position` | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk` | R | Accounting, API `GET /cash` | 101 + 102 (paying both leaves $160) |
| `list_payments` | `payments` | R | Accounting, Facilities | 101 + 102 (never pay twice) |
| `add_ticket_note` | `tickets` (notes, append-only), `desk` | W | all 5 | All: findings, DRAFT customer replies |
| `update_ticket_status` | `tickets` (status + logged reason), `desk` | W | Boss | All: next state |
| `request_payment` | `approval_requests` (new), `leases`/`invoices`, `cash_accounts`, `tickets`, `desk` | W (prepares only) | Accounting | 101 (invoice 501), 102 (rent) |
| `request_purchase` | `approval_requests`, `vendors`, `inventory`, `pricing`, `tickets`, `desk` | W (prepares only) | Inventory | Restocks when a committed order is short |
| `list_approval_requests` | `approval_requests` | R | Boss, Inventory, Accounting, Facilities; API `GET /approvals` | All: no duplicate requests |
| `decide_approval` | `approval_requests`, `payments`, `cash_accounts`, `invoices`, `leases`, `tickets`, `desk` | W (**moves cash**) | **API only**: approve/decline routes, never agents | 101, 102: the human's decision |

**New table `approval_requests`** (created automatically on first use, including after a reset):
- `id`, `kind` (rent / invoice / purchase), `ref_id`, `vendor_id`, `sku`, `size`, `qty`, `amount`, `account`, `ticket_id`
- `requested_by`, `reason`, `status` (pending / approved / declined), `created_at`
- `decided_by`, `decided_at`, `decision_note`, `payment_id`

It's the queue of money moves the agents prepared, waiting for a human.

## Backend API Routes (`backend/main.py`, FastAPI on http://localhost:8000)

1. `GET /tickets`: every ticket with its status and `state` = open or resolved.
2. `POST /tickets/{id}/run`: starts the agent team on that ticket in the background. Returns a `run_id` (409 if the team is already busy).
3. `GET /events?limit=&ticket_id=&run_id=&after=`: recent agent events (who, what they said, which tools and results) so the board can poll for new ones.
4. `POST /approvals/{id}/approve` `{decided_by, note}`: a human approved. Re-checks the request, then pays. **The only route that changes cash.**
5. `POST /approvals/{id}/decline` `{decided_by, note}`: a human declined. The request is marked declined and nothing is paid.
6. `GET /cash`: current checking balance from `cash_accounts`.
7. `POST /reset`: copies `data/campus_customs.db` over the working copy for a fresh run. The audit trail is kept.

Helpers:
- `GET /approvals?status=pending|approved|declined|all`: the requests waiting for those buttons.
- `GET /runs/{run_id}`: whether a run is still going, and its outcome.
- `GET /docs`: interactive API docs.

## Audit Trail (`output/audit_trail.json`)

The file is append-only. Each event is added to one JSON array, and earlier runs and resets are never wiped. Every event has:
- `ts`, `run_id`, `ticket_id`
- `seq` (order within the ticket)
- `agent`, `delegation_chain` (e.g. `Boss → Facilities → Accounting`), `depth`
- `event`

| Event | What's recorded |
|---|---|
| `ticket_start` / `ticket_end` | model, DB path, limits / the ticket's outcome |
| `task_received` | the exact task text given to that agent |
| `model_request` | what was sent to the model this step: tool results, retry prompts; running token usage |
| `model_response` | what the model returned: text and/or tool calls with full arguments, tokens for that response, running usage |
| `delegation_start` / `delegation_end` / `delegation_refused` | who asked whom for what, the report that came back, or why it was blocked |
| `money_request_blocked` | a ticket hit its cap on prepared payments/purchases |
| `agent_output` | the agent's final typed report and its usage so far |
| `human_decision` | approve or decline from the dashboard: who, which request, new balance |
| `db_reset` | the working DB was restored from the original |
| `stopped_by_limit` | which token or call cap ended the ticket |

## Safety

**Guardrails for real customers and real money**

1. **Agents prepare, humans pay.**
   - Agents can only create pending requests: `request_payment` (Accounting) or `request_purchase` (Inventory). Agents never get the tool that moves money (`decide_approval`). Only the dashboard's approve/decline routes call it, with the clicking person's name.
   - At decision time the server re-checks everything: exact amount owed, invoice still open, enough cash, not already decided, and a real human name (not "agent", "boss", etc.).
   - Purchase amounts are computed from `unit_cost`. The agent can't pick the price.
   - At most 3 prepared requests per ticket. Duplicates return the existing pending request.
2. **Least privilege.** Each agent sees only its own MCP tools, and the tool-call guard re-checks this on every call. The guard also stamps `author` and `requested_by` and pins requests to the current ticket, so agents can't impersonate each other or file against another ticket.
   - Only the Boss changes ticket status.
   - No agent can edit inventory or prices, or run raw SQL.
3. **No invented facts.** Every number comes from an MCP tool over the DB. Reports cite the tool for each fact. Tools return `error` rather than guessing.
4. **No direct customer contact.** Customer Service only writes `DRAFT` replies, and a human sends them.
   - Drafts never include unapproved discounts, guaranteed dates, or stock we don't have.
   - No personal data beyond the requester's name.
5. **Discounts need the owner.** Agents may recommend a price but never below `unit_cost`. Any discount leaves the ticket `waiting_on_approval`. No restock is bought for an order that hinges on an unapproved discount.
6. **Verify before paying.** Rent notices are checked against the lease (payee, amount, due date), `list_payments`, and pending requests. Any mismatch is a possible scam: prepare nothing and escalate.
7. **Accountability.**
   - Notes are append-only and stamped with the desk date and author, including the human on approvals and declines.
   - Every status change needs a reason.
   - Every agent step and human decision is in the audit trail.
8. **One team run at a time** (API lock), so prepared requests never race for the same cash.
   - The API only accepts browser calls from localhost.
   - `/reset` refuses while a run is active and never overwrites the original DB.

**Limits that keep token use in check** (top of `backend/main.py`, per ticket, shared by the Boss and everyone it delegates to)

| Limit | Value | Why |
|---|---|---|
| Model calls | 40 | Test runs used 15–22 per ticket |
| Tool calls | 50 | Test runs used 21–23 |
| Total tokens | 150,000 | Test runs used 44k–68k |
| Output tokens per response | 1,500 | Keeps answers short |
| Delegation depth | 2 | Boss → specialist → specialist, no deeper |
| Delegations per ticket | 6 | Stops ping-pong between agents |
| No cycles | — | An agent can't delegate to anyone already in its chain |
| Per-call timeout | 60 s | With 1 retry |

Hitting any limit stops the ticket and logs `stopped_by_limit`. The prompts also tell agents not to repeat identical tool calls, and the Boss briefs Customer Service last so it doesn't redo lookups.

**Real run (Problem 9, working DB):** all safety rules held. Both payments went through prepare → human approve; agents moved $0 themselves. No delegation was refused, no limit was hit. The biggest ticket used 17 model calls and 54k tokens (limits: 40 and 150k).

**Earlier test runs (scratch DB copies)**
- **Problem 5 (old in-terminal approval):** all 3 tickets ran end to end.
- **Problem 7, ticket 102 through the API:** Boss → Facilities → Accounting prepared request #1 for $2,400 with no cash change. `POST /approvals/1/approve` paid it ($3,400 → $1,000) and the ticket was auto-resolved. Approving as "agent" got a 400, and approving twice got a 409. `/reset` restored $3,400 and kept the audit trail.
- **Decline:** request marked declined, cash unchanged, ticket note added.

## Dashboard (`frontend/`, React + Vite + TypeScript)

"The Tomb": a Skull-and-Bones-themed board. The design and the reasons behind it are in `output/design.md`. It calls the API at `http://localhost:8000` (override with `VITE_API_URL`), and the backend's CORS allows `http://localhost:5173`.

**Start it:**
1. Backend first: in `backend/`, run `uvicorn main:app --reload --port 8000`.
2. Then the board: in `frontend/`, run `npm run dev`. This opens http://localhost:5173 in your browser.

**Agent code names:**
- Boss = **The Founder** (No. 322)
- Inventory = **Ossuary**
- Accounting = **Obol**
- Facilities = **Tombwarden**
- Customer Service = **Raven**

**What the board covers:**

| Need | Where | Route(s) |
|---|---|---|
| List the 3 tickets | Petitions to the Society | `GET /tickets` |
| Pick one, start the team | "Summon the Society" button | `POST /tickets/{id}/run`, `GET /runs/{id}` |
| Watch agents talk and work | The Séance (live log) + Circle of Bones (live state per agent) | `GET /events?after=` (every 1.5 s while running) |
| Mark resolved when the run finishes | Broken blue seal + "Resolved by the Society" stamp, with the real DB status underneath | `ticket_end` event |
| Summary per agent | "What it did" on each agent card + The Founder's Verdict | `agent_output` / `ticket_end` events |
| Human approves a payment or purchase | Seals Awaiting Your Mark (sign name → Approve & pay / Decline) | `GET /approvals`, `POST /approvals/{id}/approve` or `/decline` |
| Checking balance, drops after approval | The Vault (turns red, shows old → paid out → new) | `GET /cash` |

## Final Run Results (Problem 9)

All three tickets were run on the **working database** from the dashboard on 2026-10-13, starting from a clean reset (all 9 original tables verified identical to `campus_customs.db`).
- Payments were approved on the board, signed "Maxwell Kaspy (via Claude)" because Claude clicked Approve on the user's instruction.
- Every step was appended to `output/audit_trail.json` (135 events, including the reset and both human decisions).

| Ticket | Delegations | Model calls | Tool calls | Tokens | Cash change | DB status after |
|---|---|---|---|---|---|---|
| 101 | Boss→Inventory, Boss→Accounting, Boss→Customer Service | 17 | 20 | 54,239 | −$840.00 (invoice 501, request #1) | `waiting_on_vendor` |
| 102 | Boss→Facilities, Facilities→Accounting | 11 | 15 | 32,690 | −$2,400.00 (rent lease 1, request #2) | `resolved` |
| 103 | Boss→Inventory, Boss→Accounting, Boss→Customer Service | 16 | 19 | 51,455 | $0.00 (discount recommended; no money request) | `waiting_on_approval` |

**Cash:** $3,400.00 start → $2,560.00 → **$160.00** end, which equals `cash_accounts.checking`.

**"Resolved":** the board marks all 3 as *Resolved by the Society* because the agent team finished each run. In the database:
- **102** is fully `resolved`.
- **101** waits on the vendor to deliver the reprint.
- **103** waits on the owner's discount decision. There's no discount-approval button yet, which is a known gap.

**Where the results are:**
- `output/desk_tickets.html`: Expected vs. Actual per ticket, plus the itemized Cash tab.
- `output/resolved_tickets.json`: id, final status, outcome, each agent's contribution and approvals.
- `output/resolved_board.html`: full-page screenshots of the board for each ticket.
