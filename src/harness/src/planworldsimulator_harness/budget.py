"""Episode budget: hard caps for Pydantic AI plus a neutral status line."""

from dataclasses import dataclass

from pydantic_ai import UsageLimits
from pydantic_ai.usage import RunUsage


@dataclass(frozen=True)
class Budget:
    """One cap for the whole episode. Tokens include thinking tokens."""

    tool_calls: int = 300
    tokens: int = 2_000_000
    seconds: float = 600

    def usage_limits(self) -> UsageLimits:
        return UsageLimits(
            request_limit=None,
            tool_calls_limit=self.tool_calls,
            total_tokens_limit=self.tokens,
        )

    def describe(self) -> str:
        return (
            f"{self.tool_calls} tool calls, {_tokens(self.tokens)} tokens, "
            f"{_clock(self.seconds)} min"
        )

    def status(self, usage: RunUsage, elapsed: float) -> str:
        """Numbers only; no advice, so it does not steer the model."""
        calls = max(0, self.tool_calls - usage.tool_calls)
        tokens = max(0, self.tokens - usage.total_tokens)
        seconds = max(0.0, self.seconds - elapsed)
        return (
            f"Budget left: {calls}/{self.tool_calls} tool calls, "
            f"{_tokens(tokens)}/{_tokens(self.tokens)} tokens, {_clock(seconds)} min."
        )


def _tokens(n: int) -> str:
    return f"{n / 1e6:.1f}M" if n >= 100_000 else f"{n / 1e3:.0f}k"


def _clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"
