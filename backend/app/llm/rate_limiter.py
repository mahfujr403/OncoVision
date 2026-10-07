"""Rate limiting module using in-memory sliding window.

Reused across diagnostic LLM endpoints and authentication endpoints (Phase 6.1-D).
"""
import asyncio
import time
from typing import Dict, List


class RateLimiter:
    """In-memory rate limiter using sliding window with bounded state."""

    def __init__(self, max_tracked_keys: int = 10000):
        """Initialize the rate limiter."""
        self.requests: Dict[str, List[float]] = {}
        self.lock = asyncio.Lock()
        self.max_tracked_keys = max_tracked_keys

    async def _cleanup(self, window_seconds: int):
        """Remove expired timestamps and enforce bounded memory cap."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        keys_to_delete = []
        for key, timestamps in self.requests.items():
            valid_timestamps = [ts for ts in timestamps if ts > cutoff_time]
            if not valid_timestamps:
                keys_to_delete.append(key)
            else:
                self.requests[key] = valid_timestamps

        for key in keys_to_delete:
            del self.requests[key]

        # Evict oldest entries if total keys exceed bounded cap
        if len(self.requests) > self.max_tracked_keys:
            sorted_keys = sorted(
                self.requests.keys(),
                key=lambda k: min(self.requests[k]) if self.requests[k] else 0.0,
            )
            for k in sorted_keys[: len(self.requests) - self.max_tracked_keys]:
                del self.requests[k]

    async def check_rate_limit(self, user_id: str, max_requests: int = 20, window_seconds: int = 3600) -> bool:
        """Check if the user/key has exceeded the rate limit.

        Returns True if allowed, False if exceeded.
        """
        async with self.lock:
            await self._cleanup(window_seconds)

            timestamps = self.requests.get(user_id, [])
            if len(timestamps) >= max_requests:
                return False

            self.requests.setdefault(user_id, []).append(time.time())
            return True

    def get_remaining(self, user_id: str, max_requests: int = 20, window_seconds: int = 3600) -> int:
        """Get the number of remaining requests for a user/key in the current window."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        timestamps = self.requests.get(user_id, [])
        valid_timestamps = [ts for ts in timestamps if ts > cutoff_time]

        remaining = max_requests - len(valid_timestamps)
        return max(0, remaining)

    def get_retry_after(self, user_id: str, window_seconds: int = 3600) -> int:
        """Get the number of seconds until the earliest request expires.

        Returns 0 if no requests are recorded or all have expired.
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        timestamps = self.requests.get(user_id, [])
        valid_timestamps = [ts for ts in timestamps if ts > cutoff_time]
        if not valid_timestamps:
            return 0

        earliest_ts = min(valid_timestamps)
        delay = (earliest_ts + window_seconds) - current_time
        return max(1, int(delay) + 1)

    def reset(self) -> None:
        """Clear all tracked request timestamps (useful for test isolation)."""
        self.requests.clear()
