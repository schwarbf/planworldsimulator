"""[gen] TODO: replace with this world's MCP tools (contract: README.md).

Keep the core tools (brief, observe, note, advance, score) and add one tool per
world verb in `env.actions`. Every tool calls the shared Game with source="agent".
Reference implementation: src/worlds/bike-factory/server/mcp.py
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP


def build_mcp(game: Any) -> FastMCP:
    """Create the MCP server for this world. ``game`` is server.api.Game."""
    mcp = FastMCP("Example world", instructions="Read brief() first. Actions are queued and applied on advance().")

    # ---------- core tools (keep) ----------

    @mcp.tool()
    def brief() -> str:
        """The public brief: story, goal and actions."""
        return game.brief(source="agent")

    @mcp.tool()
    def observe() -> dict[str, Any]:
        """Everything visible now."""
        return game.observe(None, source="agent")

    @mcp.tool()
    def note(text: str) -> dict[str, Any]:
        """Record a hypothesis you are testing; it is shown in the agent panel."""
        return game.note(text, source="agent")

    @mcp.tool()
    def advance(weeks: int = 1) -> dict[str, Any]:
        """Apply the queued actions and simulate `weeks` weeks."""
        return game.advance(weeks, source="agent")

    @mcp.tool()
    def score() -> dict[str, Any]:
        """Current score (0–1) and the baseline score."""
        return game.score(source="agent")

    # ---------- world verbs (one tool per env.actions entry) ----------

    @mcp.tool()
    def invest(amount: int = 1) -> dict[str, Any]:
        """Queue an investment of `amount` (1–10) units of capacity."""
        return game.act("invest", {"amount": amount}, source="agent")

    return mcp
