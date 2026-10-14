# Dashboard Design: "The Tomb"

The Campus Customs agent dashboard (`frontend/`, React + Vite + TypeScript) is styled as the candlelit inner chamber of a Yale secret society modeled on Skull and Bones. Underneath the costume it's a working tool: a person picks a support ticket, runs five AI agents on it, watches them work in real time, and approves or declines any payment they prepare.

**The one rule we held to: the theme decorates, it never replaces meaning.** Every themed name ("The Vault", "Seals Awaiting Your Mark") is followed by a plain-English sentence saying exactly what the thing is and what happens if you click. Someone who has never heard of Skull and Bones, MCP, or AI agents should still know what every number and button does.

---

## 1. Layout: one screen, three chambers

```
┌──────────────────────────── MASTHEAD ────────────────────────────┬── THE VAULT ──┐
│ ☠ 322   The Tomb · motto · one-line plain description            │ $3,400.00     │
└──────────────────────────────────────────────────────────────────┴───────────────┘
┌─ LEFT (360px) ──────────┬─ CENTER (flexible) ─────────┬─ RIGHT (380px) ──────────┐
│ Petitions to the Society│ The Séance                  │ The Circle of Bones      │
│  (3 ticket cards +      │  (live log of the selected  │  (5 agent cards: job,    │
│   Summon buttons)       │   ticket's run)             │   live state, summary)   │
│ Seals Awaiting Your Mark│                             │ The Founder's Verdict    │
│  (approve / decline)    │                             │  (final report + draft)  │
└─────────────────────────┴─────────────────────────────┴──────────────────────────┘
  ⟲ Turn back the night: reset the database (audit log kept)
```

**Why this order:**
- **Left = what you act on.** Choose a ticket, start the agents, and approve money. All the buttons that change something are in one column, so you never hunt for them.
- **Center = what's happening.** The live log is the widest column because it holds the most text, and it scrolls itself while a run is going.
- **Right = who did it and what it came to.** Agent cards and the final verdict sit beside the log, so you can watch the play-by-play and the scoreboard at the same time.
- **Cash is in the top-right corner of the masthead,** always visible no matter what's selected, because money is the one thing that changes outside any single ticket.
- **Below 1200px wide,** the columns stack in the same order (act → watch → results).

## 2. The society: each agent has a code name, a job, and an ink color

| Agent (real role) | Code name | Sigil | Ink | Why the name |
|---|---|---|---|---|
| Boss | **The Founder** (No. 322, Head of the Order) | ☠ | gilt `#e2c275` | Founded the order and gives every order. 322 is the number long associated with Skull and Bones. |
| Inventory | **Ossuary** (Keeper of the Vaults) | ⚱ | bone `#e8dfc8` | An ossuary is a vault for bones, just as this agent tracks what's stored on the shelves. |
| Accounting | **Obol** (Master of Coin) | ⚖ | verdigris green `#86c79a` | An obol is the coin once placed with the dead to pay the ferryman, so it stands for every payment. |
| Facilities | **Tombwarden** (Guardian of the Tomb) | ♜ | slate blue `#9fb6d0` | "The Tomb" is the society's hall, and the warden guards the building. Here the building is the shop and its lease. |
| Customer Service | **Raven** (Messenger to the Outside) | ✒ | violet ink `#bba3e6` | Ravens carry letters out of the castle, and this agent drafts the letters to customers. |

**How agents read differently:**
- **Ink color everywhere.** Each agent's color is used for its name in the log, the left border of every line it writes, its tool calls, and the top edge of its card. After a minute you can follow a run just by color: gold hands off to green, green reports back.
- **Different name styles.** Code names are in blackletter (UnifrakturMaguntia, the "old manuscript" font). Ranks are in Roman capitals (Cinzel, the "carved in stone" font). Explanations are in a readable book serif (EB Garamond). Tool names and arguments are in monospace, so it's obvious which text is literally sent to the database.
- **Every card says the real job** in one plain sentence ("Accounting agent. Checks cash and unpaid bills… It can't pay anything itself; a human approves."), plus a small italic line explaining the code name.
- **Live state on each card:**
  - `not called`: dimmed to 50%, meaning the agent wasn't needed on this ticket.
  - `working`: blue pill. While the run is live, the card glows in the agent's ink and its sigil flickers like a candle. A "Right now:" line says exactly what it's doing ("Calling get_invoice_with_vendor.").
  - `done`: green pill, plus **What it did**: the agent's own summary, the database changes it made, and the list of tools it used.

## 3. The Séance (live log)

Every event from `GET /events` becomes one line in the speaking agent's ink, worded as a full sentence:

| Event | How it reads |
|---|---|
| An agent gets a task | "⚱ **Ossuary** *was summoned* (Inventory agent) with this task:" followed by the exact task text in a quote block |
| A tool call | "*calls tool* `check_stock_and_price(sku="CC-TEE-WHITE", size="S")`" |
| A tool's answer | A collapsed "*Result of* `check_stock_and_price` returned to Ossuary". Click to see the exact JSON the database returned. Collapsed by default so the story stays readable, but the raw evidence is one click away. |
| A handoff | "☠ **The Founder** *passes the candle to* ⚱ **Ossuary** (Inventory agent):" followed by the task. Blue-tinted, because handoffs are the "plot" of a run. |
| A report back / finish | Green-tinted lines with the agent's summary |
| A safety limit | Red line: "*tried to hand off work but was stopped* (a safety limit)" |
| A human decision | "✍ **Test Approver** (a human, not an agent) approved request #1: invoice payment of $840.00. The money left checking, which is now $2,560.00." |
| End of run | Gold line: "☠ **The rite is complete.** The Founder's final status for this ticket: `waiting_on_approval`" |

While a run is going, a flickering last line says "The society is deliberating… (waiting for the model's next reply)". This tells you the page isn't frozen; the model is thinking. The log polls every 1.5 s during a run and every 5 s otherwise.

Before any run, the center shows three unlit candles and states exactly what's true: "No run has happened on this ticket since the last reset."

## 4. Tickets, and how "resolved" shows up

Each ticket is a **sealed petition**: a parchment card with a red wax seal stamped ☠, its number, its type in plain words ("Customer order", "Rent notice", "Discount request"), its subject in blackletter, and the requester.

**When the agent team finishes a run on a ticket:**
- The wax seal turns **Yale blue with a crack and a ✓** (the seal is broken, so the petition has been answered).
- A tilted green **"RESOLVED BY THE SOCIETY"** stamp appears.
- The "Run" line changes from "Not run yet." to "The agent team finished its run on this ticket."

**Why we show two lines, not one.** "The agents are done" and "the shop has nothing left to do" aren't always the same thing. For ticket 101, the agents are done, but a human still has to approve the $840 invoice. So under the stamp, every card also shows the **database status** with its meaning spelled out:
- `waiting_on_approval: a human must approve a payment, purchase, or discount`
- `resolved: nothing left to do`

If a prepared payment is waiting, a red **"Needs you"** line points to the approvals panel. The stamp gives the satisfying "done" moment; the status line keeps it honest.

While a ticket is running, its card glows Yale blue, its button reads "Rite in progress…", and every Summon button is disabled. The backend runs one ticket at a time so two runs can't race for the same cash, and the button's tooltip says so.

## 5. Cash and approvals

**The Vault (masthead, top right)** shows the checking balance from `GET /cash` in large verdigris-green numerals. Underneath, it explains exactly where the number comes from (the `cash_accounts` table, as of the shop's desk date) and that it only drops when a human approves a payment.

**When the balance drops:**
- The number turns **blood red and shudders**.
- A gold coin **spins down** beside a line reading "~~$3,400.00~~ → paid out **$840.00**".
- After 9 seconds it settles back to green.

You can't miss that money left, and you see the before, the after, and the difference without doing math.

**Seals Awaiting Your Mark (left column)** lists every payment or purchase an agent prepared. Each card is a pulsing red wax-colored slip showing:
- the request number and amount,
- what it pays in plain words ("Pay vendor invoice 501"),
- which ticket it's for and which agent prepared it (in that agent's ink and code name),
- the agent's reason, word for word,
- **the consequence before you click:** "If you approve: checking goes from $3,400.00 to **$2,560.00**." This turns red if the result would be under $500, and warns if it's more than the account holds.

**How approving and declining work:**
1. You **sign your name** in the "Your name (recorded as the approver)" field. It's remembered in the browser. The backend refuses names like "agent" or "boss", so a person is always on record.
2. **Approve & pay** calls `POST /approvals/{id}/approve`, the only route that moves cash. **Decline** pays nothing.
3. A confirmation states the result ("Approved #1. $840.00 left checking; balance is now $2,560.00."), the Vault animates, and the decision appears in the Séance log.

## 6. The Founder's Verdict

After a run, the right column adds the Boss agent's final report:
- its summary,
- the status it set,
- a red "Still needs a human" list,
- for tickets with a customer, **the Raven's draft letter**. It's rendered as a slightly tilted sheet of real-looking parchment, labeled "**not sent**. A human reviews and sends it."

The panel also notes that the ticket's *current* status can differ from the status at the end of the run. For example, approving a payment moves ticket 101 from `waiting_on_approval` to `waiting_on_vendor`.

## 7. Creative choices that make it worth opening

- **A ritual instead of a form.** Starting the agents is "Summon the Society". Handoffs are "passes the candle to". The end of a run is "The rite is complete." Reset is "Turn back the night". The language makes a back-office chore feel like an event, and each phrase is immediately followed by its plain meaning.
- **Yale through and through.** Deep Yale blue (`#00356b`) is the action color (Summon buttons, broken seals), set against gilt, bone and candle black. The masthead crest is a skull over **322**. The motto "What is spoken in the Tomb stays in the Tomb" nods to the society's secrecy and to the audit trail, where everything said really is recorded.
- **Atmosphere that stays out of the way.** Faint stone-block texture in the background, slow drifting fog, flickering candle text only where something is actively happening, and gentle fade-ins on new log lines. Nothing animates unless it means something: a live agent, a pending seal, or money moving.
- **Physical metaphors for state.** Wax seals (unbroken = untouched, broken = answered), a stamped verdict, a parchment letter, and a vault that bleeds red when money leaves. People read these instantly without a legend.
- **Evidence on demand.** Every claim on screen can be traced: tool results expand to raw JSON, each agent card lists the tools it used, and approvals quote the agent's reason. It's fun to look at, and it's also an audit you can trust.
- **Readable first.** Explanations are 15–17px book serif on dark stone with high contrast. Blackletter is only used for names and titles, never for sentences you have to read. Ticket cards work with the keyboard (Tab + Enter), and the cash and messages are announced to screen readers (`aria-live`, `role="alert"`).

## 8. How it was verified

Tested against a scratch copy of the database, not the working copy:
1. Clicked **Summon the Society** on ticket 101. The log streamed live: Founder → Ossuary (tools in bone ink) → Obol → Raven. The Founder's card glowed while working, and the cards flipped to "done" with summaries.
2. The run finished. Ticket 101 showed the broken blue seal, the "Resolved by the Society" stamp, `waiting_on_approval`, and "Needs you: 1 payment".
3. A seal appeared for request #1, "Pay vendor invoice 501, $840.00", with "checking goes from $3,400.00 to $2,560.00".
4. Signed "Test Approver" and clicked **Approve & pay**. The Vault turned red and showed ~~$3,400.00~~ → paid out $840.00, the balance read **$2,560.00**, the ticket moved to `waiting_on_vendor`, and a ✍ human-decision line appeared in the log.
5. No browser console errors. TypeScript check and production build pass.
