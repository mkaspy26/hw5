"""Campus Customs backend: the 5-agent team (PydanticAI) + the API for the React board (FastAPI).

Start the API from the backend/ folder (project venv active):

    uvicorn main:app --reload --port 8000

Or run the team from the terminal without the API:

    python main.py                 # every open ticket
    python main.py --ticket 102    # one ticket

How it fits together:
- Every shop fact and change goes through ONE MCP connection to mcp_server/server.py
  (started automatically below). Each agent only sees its own MCP tools (models.SPECS).
- Agents only PREPARE payments/purchases. POST /approvals/{id}/approve, clicked by a
  human on the board, is the only thing that moves cash.
- Every agent can delegate to every other agent within the depth/count limits below,
  and never back into its own chain (no loops).
- Every agent-loop step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # before pydantic_ai is imported

import argparse
import asyncio
import json
import shutil
import sys
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.client.transports import StdioTransport
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent, CallToolsNode, ModelRequestNode, RunContext, UserPromptNode
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import CallToolFunc, MCPToolset
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from models import SPECS, AgentName, RunBudget, TeamDeps


# ============================================================================
# Config: model, paths, limits
# ============================================================================



BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"
MCP_SERVER_PATH = PROJECT_DIR / "mcp_server" / "server.py"
DB_PATH = Path(os.getenv("CC_DB_PATH") or PROJECT_DIR / "data" / "campus_customs_new.db")
AUDIT_PATH = Path(os.getenv("CC_AUDIT_PATH") or PROJECT_DIR / "output" / "audit_trail.json")

PROJECT_ENV_PATH = PROJECT_DIR / ".env"  # copy of .env.example with a real key
COURSE_ENV_PATH = PROJECT_DIR.parent / ".portkey.env"  # course secret file (fallback)
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MODEL_NAME = "gpt-6-luna"  # every agent uses this model; not overridable on purpose

# ---- Limits (per ticket, shared by the Boss and everyone it delegates to) ----
MAX_DELEGATION_DEPTH = 2  # Boss -> specialist -> specialist, no deeper
MAX_DELEGATIONS = 6  # delegate() calls per ticket
MAX_MONEY_REQUESTS = 3  # request_payment + request_purchase calls per ticket
# Measured test runs (all 3 tickets): 15-22 model calls, 21-23 tool calls, 44k-68k tokens per
# ticket. Limits leave ~2x headroom on the worst ticket, then stop the run.
LIMITS = UsageLimits(
    request_limit=40,  # model calls per ticket, across all agents
    tool_calls_limit=50,
    total_tokens_limit=150_000,
)
MAX_OUTPUT_TOKENS = 1_500  # per model response
MODEL_CALL_TIMEOUT_S = 60
AUDIT_TEXT_LIMIT = 4_000  # characters kept per logged message part


def _read_env_file(path: Path) -> None:
    """Copy KEY=value lines into the environment without overriding real env vars."""
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if value.strip():
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_read_env_file(PROJECT_ENV_PATH)
_read_env_file(COURSE_ENV_PATH)

if not os.getenv("PORTKEY_API_KEY"):
    raise SystemExit(
        f"PORTKEY_API_KEY not found. Copy .env.example to {PROJECT_ENV_PATH} and add your key "
        "(or set the PORTKEY_API_KEY environment variable)."
    )

# Portkey speaks the OpenAI API, so the OpenAI client just points at Portkey's URL.
CLIENT = AsyncOpenAI(
    api_key=os.environ["PORTKEY_API_KEY"],
    base_url=PORTKEY_BASE_URL,
    default_headers={"x-portkey-provider": "openai"},
    timeout=MODEL_CALL_TIMEOUT_S,
    max_retries=1,
)
MODEL = OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=CLIENT))
# Azure (behind Portkey) rejects function tools + reasoning on /chat/completions, so reasoning is off.
SETTINGS = OpenAIChatModelSettings(openai_reasoning_effort="none", max_tokens=MAX_OUTPUT_TOKENS)

# ============================================================================
# Audit trail: append-only output/audit_trail.json
# ============================================================================

_audit_lock = asyncio.Lock()


def _audit_clip(value: Any) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) <= AUDIT_TEXT_LIMIT:
        return value
    return text[:AUDIT_TEXT_LIMIT] + f"... [clipped, {len(text)} chars total]"


def _audit_part(part: Any) -> dict:
    if isinstance(part, ToolCallPart):
        return {"kind": "tool_call", "tool": part.tool_name, "args": part.args_as_dict(),
                "tool_call_id": part.tool_call_id}
    if isinstance(part, ToolReturnPart):
        return {"kind": "tool_result", "tool": part.tool_name, "content": _audit_clip(part.content),
                "tool_call_id": part.tool_call_id}
    if isinstance(part, RetryPromptPart):
        return {"kind": "retry", "tool": part.tool_name, "content": _audit_clip(part.content)}
    if isinstance(part, TextPart):
        return {"kind": "text", "content": _audit_clip(part.content)}
    if isinstance(part, UserPromptPart):
        return {"kind": "user_prompt", "content": _audit_clip(part.content)}
    if isinstance(part, ThinkingPart):
        return {"kind": "thinking", "chars": len(part.content)}
    return {"kind": getattr(part, "part_kind", type(part).__name__)}


def audit_usage_dict(usage: Any) -> dict:
    return {
        "requests": usage.requests,
        "tool_calls": usage.tool_calls,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
    }


async def audit_append(event: dict) -> None:
    """Add one event to the audit trail without touching earlier events."""
    async with _audit_lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        events = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
        events.append(event)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(events, indent=2, default=str) + "\n")
        os.replace(tmp, AUDIT_PATH)


async def audit_log(deps: TeamDeps, event: str, **details: Any) -> None:
    deps.step_counter[0] += 1
    await audit_append({
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_id": deps.run_id,
        "ticket_id": deps.ticket_id,
        "seq": deps.step_counter[0],
        "agent": deps.agent,
        "delegation_chain": list(deps.chain),
        "depth": deps.depth,
        "event": event,
        **details,
    })


async def audit_log_node(deps: TeamDeps, node: Any, step: int, run_usage: Any) -> None:
    """Record one step of an agent loop (one node from Agent.iter)."""
    if isinstance(node, UserPromptNode):
        await audit_log(deps, "task_received", agent_step=step, task=_audit_clip(node.user_prompt))
    elif isinstance(node, ModelRequestNode):
        await audit_log(deps, "model_request", agent_step=step, model=MODEL_NAME,
                  sending=[_audit_part(p) for p in node.request.parts],
                  usage_so_far=audit_usage_dict(run_usage))
    elif isinstance(node, CallToolsNode):
        resp = node.model_response
        await audit_log(deps, "model_response", agent_step=step, model=resp.model_name or MODEL_NAME,
                  parts=[_audit_part(p) for p in resp.parts],
                  response_usage={"input_tokens": resp.usage.input_tokens,
                                  "output_tokens": resp.usage.output_tokens},
                  usage_so_far=audit_usage_dict(run_usage))

# ============================================================================
# The agent team
# ============================================================================

AUTHOR_TOOLS = {"add_ticket_note", "update_ticket_status"}
MONEY_REQUEST_TOOLS = {"request_payment", "request_purchase"}


async def _guard_tool_call(
    ctx: RunContext[TeamDeps], call_tool: CallToolFunc, name: str, args: dict[str, Any]
) -> Any:
    """Runs before every MCP call: enforce per-agent tools, stamp who's asking,
    and cap how many money requests one ticket can prepare."""
    deps = ctx.deps
    if name not in SPECS[deps.agent].mcp_tools:
        return {"error": f"{deps.agent} is not allowed to call {name}."}
    if name in AUTHOR_TOOLS:
        args = {**args, "author": f"{deps.agent} agent"}  # agents can't sign as someone else
    if name in MONEY_REQUEST_TOOLS:
        deps.budget.money_requests += 1
        if deps.budget.money_requests > MAX_MONEY_REQUESTS:
            await audit_log(deps, "money_request_blocked", tool=name, request=args)
            return {"error": "Limit on prepared payments/purchases for this ticket reached. Stop and report."}
        args = {**args, "requested_by": f"{deps.agent} agent"}
        if deps.ticket_id is not None:
            args["ticket_id"] = deps.ticket_id  # requests are always tied to the ticket being worked
    return await call_tool(name, args)


MCP = MCPToolset(
    StdioTransport(
        command=sys.executable,
        args=[str(MCP_SERVER_PATH)],
        env={"CC_DB_PATH": str(DB_PATH)},
    ),
    id="campus-customs",
    process_tool_call=_guard_tool_call,
    tool_error_behavior="failed",  # the model sees the error instead of retrying blindly
)


def _team_directory(me: AgentName) -> str:
    return "\n".join(f"- {s.name}: {s.role}" for s in SPECS.values() if s.name != me)


def _build(name: AgentName) -> Agent[TeamDeps, Any]:
    spec = SPECS[name]
    agent = Agent(
        MODEL,
        name=name,
        deps_type=TeamDeps,
        output_type=spec.output_type,
        toolsets=[MCP.filtered(lambda ctx, tool, allowed=spec.mcp_tools: tool.name in allowed)],
        model_settings=SETTINGS,
        retries=2,
    )

    @agent.instructions
    def prompt(ctx: RunContext[TeamDeps]) -> str:
        # Re-read each run so prompt edits apply without code changes.
        return (PROMPTS_DIR / spec.prompt_file).read_text()

    @agent.instructions
    def situation(ctx: RunContext[TeamDeps]) -> str:
        d = ctx.deps
        chain = " -> ".join(d.chain)
        left = MAX_DELEGATIONS - d.budget.delegations
        return (
            f"## This run\nYou are the {name} agent. Ticket: {d.ticket_id}. "
            f"Delegation chain so far: {chain} (depth {d.depth} of max {MAX_DELEGATION_DEPTH}). "
            f"Delegations left for this ticket: {left}.\n\n## Your teammates (use `delegate`)\n"
            f"{_team_directory(name)}"
        )

    @agent.tool
    async def delegate(ctx: RunContext[TeamDeps], to: AgentName, task: str) -> dict:
        """Hand a specific task to a teammate and wait for their report.

        Args:
            to: Teammate to ask: Boss, Inventory, Accounting, Facilities, or Customer Service.
            task: Exactly what you need from them, including the ticket id and any facts
                they'll need (sku, size, qty, invoice/lease id, amounts).
        """
        d = ctx.deps
        refusal = None
        if to == d.agent:
            refusal = "You can't delegate to yourself."
        elif to in d.chain:
            refusal = f"{to} is already working on this request higher up the chain ({' -> '.join(d.chain)}); answer with what you have."
        elif d.depth >= MAX_DELEGATION_DEPTH:
            refusal = "Maximum delegation depth reached; finish this yourself or report what's missing."
        elif d.budget.delegations >= MAX_DELEGATIONS:
            refusal = "Delegation limit for this ticket reached; finish with what you have."
        if refusal:
            await audit_log(d, "delegation_refused", to=to, task=task, reason=refusal)
            return {"error": refusal}

        d.budget.delegations += 1
        child = TeamDeps(
            agent=to, run_id=d.run_id, ticket_id=d.ticket_id, chain=[*d.chain, to],
            budget=d.budget, step_counter=d.step_counter,
        )
        await audit_log(d, "delegation_start", to=to, task=task)
        report = await run_agent(to, task, child, usage=ctx.usage)  # shared token budget
        await audit_log(d, "delegation_end", to=to, report=report.model_dump())
        return report.model_dump()

    return agent


AGENTS: dict[AgentName, Agent[TeamDeps, Any]] = {name: _build(name) for name in SPECS}


async def run_agent(name: AgentName, task: str, deps: TeamDeps, usage=None):
    """One agent loop: model -> tools -> model ... -> structured output, logging every step."""
    agent = AGENTS[name]
    async with agent.iter(task, deps=deps, usage=usage, usage_limits=LIMITS) as run:
        step = 0
        async for node in run:
            step += 1
            await audit_log_node(deps, node, step, run.usage)
    output = run.result.output
    await audit_log(deps, "agent_output", output=output.model_dump(), usage_so_far=audit_usage_dict(run.usage))
    return output


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]


async def handle_ticket(ticket_id: int, run_id: str) -> dict:
    """Hand one ticket to the Boss and return its TicketOutcome (or the limit error)."""
    deps = TeamDeps(agent="Boss", run_id=run_id, ticket_id=ticket_id, chain=["Boss"], budget=RunBudget())
    task = (
        f"Handle ticket {ticket_id}. Read it, get the facts you need from your team, "
        "take the allowed actions, set the ticket's status, and report the outcome."
    )
    await audit_log(deps, "ticket_start", model=MODEL_NAME, db=str(DB_PATH), limits=asdict(LIMITS))
    try:
        outcome = (await run_agent("Boss", task, deps)).model_dump()
    except UsageLimitExceeded as exc:
        await audit_log(deps, "stopped_by_limit", error=str(exc))
        outcome = {"ticket_id": ticket_id, "error": f"Stopped by usage limit: {exc}"}
    await audit_log(deps, "ticket_end", outcome=outcome)
    return outcome

# ============================================================================
# API routes for the React board
# ============================================================================

ORIGINAL_DB = PROJECT_DIR / "data" / "campus_customs.db"

# In-memory record of agent runs started through the API (cleared on restart).
RUNS: dict[str, dict[str, Any]] = {}
_run_lock = asyncio.Lock()  # one team run at a time, so prepared requests never race for cash


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with MCP:  # one MCP server process for the life of the API
        yield


app = FastAPI(title="Campus Customs backend", lifespan=lifespan)
# Browsers only let the Vite dashboard (http://localhost:5173) call this API if we list its origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",  # if Vite picks another local port
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mcp(tool: str, args: dict | None = None) -> dict:
    """Call one MCP tool; turn its {"error": ...} replies into HTTP errors."""
    result = await MCP.direct_call_tool(tool, args or {})
    if isinstance(result, dict) and "error" in result:
        msg = result["error"]
        code = 404 if msg.startswith("No ") else 409 if "already" in msg else 400
        raise HTTPException(status_code=code, detail=msg)
    return result


def _system_deps(ticket_id: int | None = None) -> TeamDeps:
    # For audit events the API itself writes (resets, human decisions).
    return TeamDeps(agent="Boss", run_id="api", ticket_id=ticket_id, chain=["Boss"], budget=RunBudget())


# ------------------------------------------------------------------ tickets


@app.get("/tickets")
async def list_tickets() -> dict:
    """1. Every ticket, with its status and whether it's open or resolved."""
    data = await mcp("list_tickets")
    for t in data["tickets"]:
        t["state"] = "resolved" if t["resolved"] else "open"
    return data


@app.post("/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int) -> dict:
    """2. Start the agent team on one ticket. Runs in the background; poll
    GET /runs/{run_id} for the outcome and GET /events for live steps."""
    await mcp("get_ticket", {"ticket_id": ticket_id})  # 404 if it doesn't exist
    if _run_lock.locked():
        raise HTTPException(409, "The team is already working on a ticket; wait for it to finish.")
    run_id = new_run_id()
    RUNS[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "running",
                    "started_at": datetime.now().astimezone().isoformat(timespec="seconds")}

    async def work() -> None:
        async with _run_lock:
            try:
                outcome = await handle_ticket(ticket_id, run_id)
                RUNS[run_id].update(status="error" if "error" in outcome else "done", outcome=outcome)
            except Exception as exc:  # surface failures to the dashboard instead of losing them
                RUNS[run_id].update(status="error", outcome={"error": f"{type(exc).__name__}: {exc}"})
            RUNS[run_id]["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")

    asyncio.create_task(work())
    return RUNS[run_id]


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    """Status (running / done / error) and outcome of a run started above."""
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} (runs are forgotten when the server restarts).")
    return RUNS[run_id]


# ------------------------------------------------------------------- events


def _summarize(idx: int, e: dict) -> dict:
    """Turn one audit-trail event into what the board shows: who, what they said, which tools."""
    out = {k: e.get(k) for k in ("ts", "run_id", "ticket_id", "agent", "event", "delegation_chain")}
    out.update(id=idx, said=None, tools=[], tool_results=[])
    kind = e.get("event")
    if kind == "model_response":
        texts = [p["content"] for p in e.get("parts", []) if p["kind"] == "text" and p.get("content")]
        out["said"] = "\n".join(texts) or None
        out["tools"] = [{"tool": p["tool"], "args": p.get("args")} for p in e.get("parts", [])
                        if p["kind"] == "tool_call" and p["tool"] != "final_result"]
    elif kind == "model_request":
        out["tool_results"] = [{"tool": p["tool"], "result": p.get("content")} for p in e.get("sending", [])
                               if p["kind"] == "tool_result" and p["tool"] != "final_result"]
    elif kind == "task_received":
        out["said"] = f"Received task: {e.get('task')}"
    elif kind == "delegation_start":
        out["said"] = f"Asked {e.get('to')}: {e.get('task')}"
    elif kind == "delegation_end":
        out["said"] = f"{e.get('to')} reported: {(e.get('report') or {}).get('summary')}"
    elif kind == "delegation_refused":
        out["said"] = f"Delegation to {e.get('to')} refused: {e.get('reason')}"
    elif kind == "agent_output":
        out["said"] = (e.get("output") or {}).get("summary")
        out["output"] = e.get("output")  # full report: actions_taken, needs_human, status
    elif kind == "ticket_end":
        out["output"] = e.get("outcome")
        out["said"] = (e.get("outcome") or {}).get("summary") or (e.get("outcome") or {}).get("error")
    elif kind == "human_decision":
        req = e.get("request") or {}
        out["output"] = {k: e.get(k) for k in ("decision", "decided_by", "request", "new_balance")}
        out["said"] = (f"{e.get('decided_by')} {e.get('decision')}d request #{req.get('id')} "
                       f"({req.get('kind')} ${req.get('amount')})")
    elif kind in ("db_reset", "stopped_by_limit", "money_request_blocked"):
        out["output"] = {k: v for k, v in e.items() if k not in out and k != "seq"}
        out["said"] = e.get("error") or e.get("reason") or kind.replace("_", " ")
    return out


@app.get("/events")
async def recent_events(
    limit: int = Query(50, ge=1, le=500),
    ticket_id: int | None = None,
    run_id: str | None = None,
    after: int | None = Query(None, description="Only events with id > after (for polling)"),
) -> dict:
    """3. Recent agent events (newest last): what each agent said and which tools it used."""
    events = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []

    def keep(i: int, e: dict) -> bool:
        if after is not None and i <= after:
            return False
        if ticket_id is not None and e.get("ticket_id") != ticket_id:
            return False
        if run_id is not None and e.get("run_id") != run_id:
            return False
        # model_request steps only matter to the board when they carry tool results back
        if e.get("event") == "model_request":
            return any(p["kind"] == "tool_result" for p in e.get("sending", []))
        return True

    rows = [_summarize(i, e) for i, e in enumerate(events) if keep(i, e)][-limit:]
    return {"events": rows, "last_id": len(events) - 1, "running": _run_lock.locked()}


# ---------------------------------------------------------------- approvals


class Decision(BaseModel):
    decided_by: str = Field(min_length=2, description="Full name of the human clicking the button")
    note: str = ""


@app.get("/approvals")
async def list_approvals(status: Literal["pending", "approved", "declined", "all"] = "pending") -> dict:
    """Payments and purchases the agents prepared, waiting for (or past) a human decision."""
    return await mcp("list_approval_requests", {"status": status})


async def _decide(request_id: int, decision: str, body: Decision) -> dict:
    result = await mcp("decide_approval", {"request_id": request_id, "decision": decision,
                                           "decided_by": body.decided_by, "note": body.note})
    req = result["request"]
    await audit_log(_system_deps(req.get("ticket_id")), "human_decision", decision=decision,
                    decided_by=body.decided_by, request=req, new_balance=result.get("new_balance"))
    return result


@app.post("/approvals/{request_id}/approve")
async def approve(request_id: int, body: Decision) -> dict:
    """4. A human approved: re-check the request, then actually pay (the only route that changes cash)."""
    return await _decide(request_id, "approve", body)


@app.post("/approvals/{request_id}/decline")
async def decline(request_id: int, body: Decision) -> dict:
    """5. A human declined: mark the request declined. Nothing is paid."""
    return await _decide(request_id, "decline", body)


# --------------------------------------------------------------------- cash


@app.get("/cash")
async def checking_balance() -> dict:
    """6. Current checking balance from cash_accounts."""
    data = await mcp("get_cash_position")
    checking = next((a for a in data["cash_accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No checking account in cash_accounts.")
    return {"account": "checking", "balance": checking["balance"], "as_of": checking["date"],
            "desk_date": data["desk_date"]}


# -------------------------------------------------------------------- reset


@app.post("/reset")
async def reset_database() -> dict:
    """7. Copy the original database over the working copy for a fresh run.
    The audit trail is kept (it's append-only); a db_reset event is added."""
    if _run_lock.locked():
        raise HTTPException(409, "Can't reset while the team is working on a ticket.")
    if DB_PATH.resolve() == ORIGINAL_DB.resolve():
        raise HTTPException(500, "Working database path points at the original; refusing to overwrite it.")
    shutil.copyfile(ORIGINAL_DB, DB_PATH)
    await audit_log(_system_deps(), "db_reset", source=str(ORIGINAL_DB), target=str(DB_PATH))
    return {"reset": True, "tickets": (await list_tickets())["tickets"], "cash": await checking_balance()}


@app.get("/")
async def index() -> dict:
    return {"service": "Campus Customs backend", "db": str(DB_PATH), "docs": "/docs"}

# ============================================================================
# Terminal mode: python main.py [--ticket N]
# ============================================================================

async def cli() -> None:
    parser = argparse.ArgumentParser(description="Run the agent team on tickets from the terminal (no web server).")
    parser.add_argument("--ticket", type=int, action="append", help="ticket id (repeatable); default: all open")
    args = parser.parse_args()

    run_id = new_run_id()
    async with MCP:  # one MCP server process for the whole run
        tickets = args.ticket or [t["id"] for t in (await MCP.direct_call_tool("list_open_tickets", {}))["tickets"]]
        for ticket_id in tickets:  # one at a time, so requests never race each other
            print(f"\n--- Ticket {ticket_id} ---")
            print(json.dumps(await handle_ticket(ticket_id, run_id), indent=2))





if __name__ == "__main__":
    asyncio.run(cli())
