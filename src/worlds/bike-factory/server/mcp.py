"""[gen] MCP tools for Bike Factory. Every tool calls the shared Game, which logs the call."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

SITES = "tier2, tier1, components, assembly, warehouse, storeA, storeB, storeC (Easy: tier1, assembly, warehouse, storeA, storeB)"


def build_mcp(game: Any) -> FastMCP:
    """Create the MCP server for this world. ``game`` is server.api.Game."""
    mcp = FastMCP(
        "Bike Factory",
        instructions="Run a bike supply chain for 52 weeks. Read brief() first. Actions are queued and applied on advance().",
    )

    @mcp.tool()
    def brief() -> str:
        """The public brief: story, goal and actions."""
        return game.brief(source="agent")

    @mcp.tool()
    def observe() -> dict[str, Any]:
        """Everything visible now: week, cash, storm, and per site stock, incoming, backlog, capacity, lead, demand, sold."""
        return game.observe(None, source="agent")

    @mcp.tool(description=f"Visible values of one site. Sites: {SITES}.")
    def observe_site(site: str) -> dict[str, Any]:
        return game.observe(site, source="agent")

    @mcp.tool()
    def order(site: str, qty: int) -> dict[str, Any]:
        """Queue an order of `qty` units (1–500) at `site`; its upstream site ships them (the top supplier buys raw parts at CHF 150)."""
        return game.act("order", {"site": site, "qty": qty}, source="agent")

    @mcp.tool()
    def expand(site: str) -> dict[str, Any]:
        """Queue an expansion of a non-store site: +20% capacity, +8% holding cost; CHF 8k (warehouse 12k). Not on Easy."""
        return game.act("expand", {"site": site}, source="agent")

    @mcp.tool()
    def probe(site: str) -> dict[str, Any]:
        """Queue a probe of `site` (CHF 500); on advance it may reveal a hidden rule there."""
        return game.act("probe", {"site": site}, source="agent")

    @mcp.tool()
    def cancel(index: int) -> dict[str, Any]:
        """Remove queued action `index` (0-based, as listed in observe()["queued"]) before advance()."""
        return game.unqueue(index, source="agent")

    @mcp.tool()
    def note(text: str) -> dict[str, Any]:
        """Record a hypothesis you are testing; it is shown in the agent panel."""
        return game.note(text, source="agent")

    @mcp.tool()
    def advance(weeks: int = 1) -> dict[str, Any]:
        """Apply the queued actions and simulate `weeks` weeks (one step = one week)."""
        return game.advance(weeks, source="agent")

    @mcp.tool()
    def score() -> dict[str, Any]:
        """Current score (0–1), profit, customers served and the baseline score."""
        return game.score(source="agent")

    return mcp
