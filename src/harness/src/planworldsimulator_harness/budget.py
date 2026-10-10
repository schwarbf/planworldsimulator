"""Episode budget: hard caps for Pydantic AI plus a neutral status line."""

from dataclasses import dataclass

from pydantic_ai import UsageLimits
from pydantic_ai.usage import RunUsage

# Hidden safety ceiling against tool-call loops; not part of the budget the agent sees.
SAFETY_TOOL_CALLS = 2000


@dataclass(frozen=True)
class Budget:
    """One cap for the whole episode. Tokens include tool calls and thinking."""

    tokens: int = 2_000_000
    seconds: float = 1800  # loose safety cap; tokens are the main budget

    def usage_limits(self) -> UsageLimits:
        return UsageLimits(
            request_limit=None,
            tool_calls_limit=SAFETY_TOOL_CALLS,
            total_tokens_limit=self.tokens,
        )

    def describe(self) -> str:
        return f"{_tokens(self.tokens)} tokens, {_clock(self.seconds)} min"

    def status(self, usage: RunUsage, elapsed: float) -> str:
        """Numbers only; no advice, so it does not steer the model."""
        tokens = max(0, self.tokens - usage.total_tokens)
        seconds = max(0.0, self.seconds - elapsed)
        return (
            f"Budget left: {_tokens(tokens)}/{_tokens(self.tokens)} tokens, "
            f"{_clock(seconds)} min."
        )


def _tokens(n: int) -> str:
    return f"{n / 1e6:.1f}M" if n >= 100_000 else f"{n / 1e3:.0f}k"


def _clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"
