"""In-memory per-user rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


class RateLimitExceeded(RuntimeError):
    """Raised when a user exceeds command threshold."""


@dataclass(frozen=True)
class LimitPolicy:
    max_events: int
    window_sec: int


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[int, str], deque[float]] = defaultdict(deque)

    def check(self, user_id: int, channel: str, policy: LimitPolicy) -> None:
        now = time.time()
        key = (user_id, channel)
        q = self._events[key]

        while q and now - q[0] > policy.window_sec:
            q.popleft()

        if len(q) >= policy.max_events:
            raise RateLimitExceeded(
                f"rate limit exceeded for user={user_id}, channel={channel}"
            )

        q.append(now)
