import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    """In-memory per-key limiter. One process only, which matches the SQLite setup."""

    def __init__(self, max_events: int, window_seconds: float) -> None:
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, now: float | None = None) -> int | None:
        """Record an event. Returns seconds to wait when over the limit, else None."""
        now = time.monotonic() if now is None else now
        events = self._events[key]
        while events and events[0] <= now - self.window_seconds:
            events.popleft()
        if len(events) >= self.max_events:
            return max(1, int(events[0] + self.window_seconds - now) + 1)
        events.append(now)
        return None
