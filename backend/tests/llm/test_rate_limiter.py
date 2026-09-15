"""Unit tests for the LLM sliding window rate limiter."""

import asyncio
from app.llm.rate_limiter import RateLimiter


def test_rate_limiter_allows_under_limit():
    async def _run():
        limiter = RateLimiter()
        user_id = "user-123"

        for _ in range(5):
            allowed = await limiter.check_rate_limit(user_id, max_requests=5, window_seconds=60)
            assert allowed is True

        # 6th request should fail
        allowed = await limiter.check_rate_limit(user_id, max_requests=5, window_seconds=60)
        assert allowed is False

    asyncio.run(_run())


def test_rate_limiter_remaining_count():
    async def _run():
        limiter = RateLimiter()
        user_id = "user-456"

        assert limiter.get_remaining(user_id, max_requests=10, window_seconds=60) == 10

        await limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60)
        await limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60)

        assert limiter.get_remaining(user_id, max_requests=10, window_seconds=60) == 8

    asyncio.run(_run())


def test_rate_limiter_different_users():
    async def _run():
        limiter = RateLimiter()
        user_a = "user-a"
        user_b = "user-b"

        for _ in range(3):
            await limiter.check_rate_limit(user_a, max_requests=3, window_seconds=60)

        # user_a is now at limit
        assert await limiter.check_rate_limit(user_a, max_requests=3, window_seconds=60) is False

        # user_b should still be allowed
        assert await limiter.check_rate_limit(user_b, max_requests=3, window_seconds=60) is True

    asyncio.run(_run())
