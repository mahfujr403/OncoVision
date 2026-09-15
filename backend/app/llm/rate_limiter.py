"""
Rate limiting module for LLM API usage.
"""
import asyncio
import time
from typing import Dict, List

class RateLimiter:
    """In-memory rate limiter using sliding window."""

    def __init__(self):
        """Initialize the rate limiter."""
        self.requests: Dict[str, List[float]] = {}
        self.lock = asyncio.Lock()

    async def _cleanup(self, window_seconds: int):
        """Remove expired timestamps."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        keys_to_delete = []
        for user_id, timestamps in self.requests.items():
            valid_timestamps = [ts for ts in timestamps if ts > cutoff_time]
            if not valid_timestamps:
                keys_to_delete.append(user_id)
            else:
                self.requests[user_id] = valid_timestamps
                
        for key in keys_to_delete:
            del self.requests[key]

    async def check_rate_limit(self, user_id: str, max_requests: int = 20, window_seconds: int = 3600) -> bool:
        """
        Check if the user has exceeded the rate limit.
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
        """
        Get the number of remaining requests for a user in the current window.
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        timestamps = self.requests.get(user_id, [])
        valid_timestamps = [ts for ts in timestamps if ts > cutoff_time]
        
        remaining = max_requests - len(valid_timestamps)
        return max(0, remaining)
