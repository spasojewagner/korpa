"""In-memory request limits that keep the model within its free quota (single API instance)."""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date


@dataclass
class RateLimiter:
    per_minute: int = 10
    per_day: int | None = 500
    _recent: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _day: date = field(default_factory=date.today)
    _today: int = 0

    def check(self, client: str, now: float | None = None, today: date | None = None) -> int | None:
        """Record a request; return None if allowed, else seconds to wait."""
        now = time.monotonic() if now is None else now
        today = date.today() if today is None else today
        if today != self._day:
            self._day, self._today = today, 0
            self._recent.clear()
        if self.per_day is not None and self._today >= self.per_day:
            return 3600
        window = self._recent[client]
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= self.per_minute:
            return max(1, int(60 - (now - window[0])) + 1)
        window.append(now)
        self._today += 1
        return None
