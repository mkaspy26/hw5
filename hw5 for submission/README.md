# Campus Customs: Agent Team, MCP Server & "The Tomb" Dashboard (hw5)

A five-agent back office for **Campus Customs**, a small Yale apparel shop. The agents work the shop's support tickets, and a human approves any money they want to spend.

- **Agents:** PydanticAI, model `gpt-6-luna` via Portkey. Boss, Inventory, Accounting, Facilities, Customer Service.
- **MCP server:** FastMCP, 17 tools. It's the only way anything reads or changes the shop's SQLite database.
- **Backend:** FastAPI.
- **Dashboard:** React + Vite + TypeScript, themed after Yale's Skull and Bones.

The full design reference is [`output/harness.md`](output/harness.md); the dashboard design is [`output/design.md`](output/design.md).

```
hw5/
├── README.md, requirements.txt, .env.example, .gitignore, .mcp.json, AI_prompts.md
├── data/
│   ├── campus_customs.db        ← ORIGINAL (never modified)
│   └── campus_customs_new.db    ← WORKING COPY (agents + API read and write here)
├── mcp_server/server.py         ← FastMCP server: 17 tools over the working copy
├── backend/
│   ├── main.py                  ← agent team + audit trail + limits + FastAPI routes
│   ├── models.py                ← data types + the 5 agent definitions (allowed tools)
│   └── prompts/                 ← one detailed prompt per agent
├── frontend/                    ← React board ("The Tomb")
└── output/                      ← harness, plans, results, audit trail, screenshots page
```

---

## 0. One-time setup

You need Python 3.12+ (built with 3.14), Node.js 20+, and a Portkey API key.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env           # then open .env and paste your real PORTKEY_API_KEY
cd frontend && npm install && cd ..
```

`.env` is git-ignored. Never commit your real key.

## 1. Copy the original DB to the working copy (whenever you want a clean run)

Agents and the API only touch `data/campus_customs_new.db`. To start over from the original data (3 open tickets, $3,400.00 in checking, no payments), run this with the backend **stopped**:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

If the backend is already running, use the reset route in step 5 instead. It does the same copy safely and logs it.

## 2. Start the MCP server

The MCP server is the shop's toolbox (stock, prices, invoices, lease, cash, ticket notes, prepared payments). You can run it on its own to check it starts, or to use it from Claude Code (it's registered in `.mcp.json` as `campus-customs`):

```bash
.venv/bin/python mcp_server/server.py
```

It talks over stdin/stdout, so it just waits silently; stop it with Ctrl+C. **You don't need to start it by hand for the dashboard.** The backend in step 3 launches its own copy of `mcp_server/server.py` automatically and keeps one connection open while the API runs.

## 3. Start the FastAPI backend

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

The API runs at **http://localhost:8000**, with interactive docs at http://localhost:8000/docs.

| Route | What it does |
|---|---|
| `GET /tickets` | All tickets, each marked open or resolved |
| `POST /tickets/{id}/run` | Start the agent team on one ticket (in the background) |
| `GET /runs/{run_id}` | Whether that run is still going, and its outcome |
| `GET /events?after=N` | Recent agent events: who said what and which tools they used |
| `GET /approvals` | Payments/purchases the agents prepared |
| `POST /approvals/{id}/approve` | A human approves. **The only route that moves cash.** |
| `POST /approvals/{id}/decline` | A human declines; nothing is paid |
| `GET /cash` | Checking balance from `cash_accounts` |
| `POST /reset` | Copy the original DB over the working copy (audit trail kept) |

Terminal-only alternative, without the board: `python main.py --ticket 102` from `backend/`.

## 4. Start the React board

In a second terminal, with the backend running:

```bash
cd frontend
npm run dev
```

This opens **http://localhost:5173**. The board calls the backend at `http://localhost:8000` (override with `VITE_API_URL`), and the backend allows that origin (CORS). Adding `?ticket=102` to the address opens the board on that ticket.

## 5. Reset the DB before a full 3-ticket run

Always start a full run of tickets 101, 102 and 103 from clean data. With the backend running, either:
- click **"⟲ Turn back the night"** at the bottom of the board and confirm, or
- run `curl -X POST http://localhost:8000/reset`.

Checking should read **$3,400.00** and all three tickets should be `open`.

**Then, for each ticket 101 → 102 → 103:**
1. Click **Summon the Society** on the ticket and watch the Séance (live log) and the Circle of Bones (agent cards).
2. When the run ends, the ticket gets a broken seal and a "Resolved by the Society" stamp. Its real database status is shown underneath.
3. If a seal appears under **Seals Awaiting Your Mark**, type your name and click **Approve & pay** or **Decline**. The Vault (checking balance) drops only when you approve.

**Expected result** (the Problem 9 run):

| Ticket | Approval | Checking after | Status after |
|---|---|---|---|
| 101 | Pay invoice 501, $840.00 | $2,560.00 | `waiting_on_vendor` |
| 102 | Pay rent, $2,400.00 | $160.00 | `resolved` |
| 103 | None (discount needs the owner) | $160.00 | `waiting_on_approval` |

---

## Safety in one paragraph
- **Money:** agents can only *prepare* payments and purchases. A named human must approve each one, and the server re-checks the amount, the bill's status and the funds at that moment.
- **Least privilege:** each agent can call only its own MCP tools. Only Accounting/Inventory prepare money requests, and only the Boss changes a ticket's status.
- **Customers:** Customer Service writes drafts that a human sends, and drafts never include unapproved discounts.
- **Token limits per ticket:** 40 model calls, 50 tool calls, 150k tokens. Delegation goes at most 2 levels deep, with at most 6 handoffs and no loops.
- **Audit:** every step is appended to `output/audit_trail.json`, which is never wiped.

## Outputs
| File | What it is |
|---|---|
| `output/harness.md` | Tables, MCP tools, agents, routes, dashboard, safety, final results |
| `output/mcp_smoke.json` | Evidence that the first 3 MCP tools return database values |
| `output/desk_tickets.html` | Per ticket: Expected plan vs. Actual run, plus the Cash and Reflections tabs |
| `output/design.md` | Dashboard design choices |
| `output/resolved_tickets.json` | Final status, outcome, each agent's contribution and the approvals per ticket |
| `output/resolved_board.html` | Screenshots of the board for each resolved ticket |
| `output/audit_trail.json` | Every agent step and human decision from the real run |
| `output/github_url.txt` | Link to this repository |
