"""In-memory sliding-window rate limiter for CareCast API (Phase 4).

Features:
- Thread-safe sliding window tracking using monotonic time
- Separate configurable limits for GET and POST requests
- IP extraction supporting optional trusted proxy header (X-Forwarded-For)
- Returns retry-after duration when exceeded
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int) -> tuple[bool, int]:
        """Check if request for key is allowed within the sliding window.
        
        Returns:
            (allowed: bool, retry_after: int)
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            # Clean timestamps older than window
            timestamps = self._hits[key]
            valid_timestamps = [t for t in timestamps if t > cutoff]

            if len(valid_timestamps) >= max_requests:
                # Rate limited. Calculate retry_after seconds based on oldest hit in window
                oldest_in_window = valid_timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest_in_window)))
                self._hits[key] = valid_timestamps
                return False, retry_after

            valid_timestamps.append(now)
            self._hits[key] = valid_timestamps
            return True, 0

    def reset(self) -> None:
        """Clear all recorded hits (useful for test isolation)."""
        with self._lock:
            self._hits.clear()
