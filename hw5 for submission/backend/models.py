"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["Boss", "Inventory", "Accounting", "Facilities", "Customer Service"]
TicketStatus = Literal[
    "open",
    "in_progress",
    "waiting_on_vendor",
    "waiting_on_approval",
    "waiting_on_customer",
    "resolved",
]


# ------------------------------------------------------------ agent outputs


class Fact(BaseModel):
    """One shop fact, tied to the MCP tool call it came from."""

    detail: str = Field(description="The fact, with exact numbers/dates as the tool returned them.")
    source_tool: str = Field(description="MCP tool that returned it, e.g. check_stock_and_price.")


class SpecialistReport(BaseModel):
    """What Inventory, Accounting, Facilities, or Customer Service hands back."""

    agent: AgentName
    ticket_id: int | None
    summary: str = Field(description="2-4 sentences: what you found and what you did.")
    facts: list[Fact] = Field(default_factory=list)
    actions_taken: list[str] = Field(
        default_factory=list, description="Database changes you made (notes, prepared requests). Empty if none."
    )
    recommendations: list[str] = Field(default_factory=list)
    needs_human: list[str] = Field(
        default_factory=list, description="Decisions or sends only a person can do."
    )
    suggested_status: TicketStatus | None = None


class TicketOutcome(BaseModel):
    """The Boss's final word on one ticket."""

    ticket_id: int
    final_status: TicketStatus
    summary: str = Field(description="What happened on this ticket, in plain English.")
    agents_consulted: list[AgentName] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    needs_human: list[str] = Field(default_factory=list)
    customer_reply_draft: str | None = Field(
        default=None, description="Draft message to the requester for a human to review and send."
    )


# ------------------------------------------------------- run-time plumbing

@dataclass
class RunBudget:
    """Counters shared by every agent working on one ticket."""

    delegations: int = 0
    money_requests: int = 0  # request_payment / request_purchase calls


@dataclass
class TeamDeps:
    """Passed to every agent run. `chain` is who delegated to whom, Boss first."""

    agent: AgentName
    run_id: str
    ticket_id: int | None
    chain: list[AgentName]
    budget: RunBudget
    step_counter: list[int] = field(default_factory=lambda: [0])  # shared across the ticket

    @property
    def depth(self) -> int:
        return len(self.chain) - 1


# ------------------------------------------------------ the five agents
# Each agent's identity: its prompt file in backend/prompts/, a one-line role
# (shown to teammates in their delegate tool), the ONLY MCP tools it may call,
# and the typed report it must return.


@dataclass(frozen=True)
class AgentSpec:
    name: AgentName
    prompt_file: str
    role: str
    mcp_tools: frozenset[str]
    output_type: type[BaseModel]


BOSS = AgentSpec(
    name="Boss",
    prompt_file="boss.md",
    role="Shop manager. Triages each ticket, assigns work, sets the ticket's status, and signs off.",
    mcp_tools=frozenset({
        "list_open_tickets", "list_tickets", "get_ticket", "update_ticket_status", "add_ticket_note",
        "list_approval_requests",
    }),
    output_type=TicketOutcome,
)

INVENTORY = AgentSpec(
    name="Inventory",
    prompt_file="inventory.md",
    role="Stock and restocking. Knows what's on hand per size, which vendor can restock and how fast; prepares restock purchases for human approval.",
    mcp_tools=frozenset({
        "get_ticket", "check_stock_and_price", "get_stock_all_sizes", "list_vendors",
        "get_invoice_with_vendor", "request_purchase", "list_approval_requests", "add_ticket_note",
    }),
    output_type=SpecialistReport,
)

ACCOUNTING = AgentSpec(
    name="Accounting",
    prompt_file="accounting.md",
    role="Money. Cash position, vendor invoices, preparing payments for human approval, and pricing/discount math.",
    mcp_tools=frozenset({
        "get_ticket", "get_invoice_with_vendor", "get_lease_and_cash", "get_cash_position",
        "list_payments", "quote_bulk_price", "request_payment", "list_approval_requests", "add_ticket_note",
    }),
    output_type=SpecialistReport,
)

FACILITIES = AgentSpec(
    name="Facilities",
    prompt_file="facilities.md",
    role="The shop space. Verifies rent notices against the lease and owns the landlord relationship.",
    mcp_tools=frozenset({"get_ticket", "get_lease_and_cash", "list_payments", "list_approval_requests", "add_ticket_note"}),
    output_type=SpecialistReport,
)

CUSTOMER_SERVICE = AgentSpec(
    name="Customer Service",
    prompt_file="customer_service.md",
    role="Customers and student groups. Drafts every reply to a requester (a human sends it).",
    mcp_tools=frozenset({
        "get_ticket", "check_stock_and_price", "get_stock_all_sizes", "quote_bulk_price",
        "add_ticket_note",
    }),
    output_type=SpecialistReport,
)

SPECS: dict[str, AgentSpec] = {s.name: s for s in (BOSS, INVENTORY, ACCOUNTING, FACILITIES, CUSTOMER_SERVICE)}
