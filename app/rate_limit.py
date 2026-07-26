from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Small fixed-window limiter for the single-replica baseline."""

    def __init__(
        self, *, read_limit: int = 60, write_limit: int = 20, window: float = 60.0
    ) -> None:
        self.read_limit = read_limit
        self.write_limit = write_limit
        self.window = window
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, subject: str, operation: str) -> bool:
        now = time.monotonic()
        limit = self.read_limit if operation == "read" else self.write_limit
        key = (subject, operation)
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - self.window:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True
