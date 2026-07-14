import asyncio

import pytest

from std_cards.core.ratelimit import NotFoundBurstLockout, SlidingWindowRateLimiter


@pytest.mark.asyncio
async def test_sliding_window_allows_under_limit():
    limiter = SlidingWindowRateLimiter()
    for i in range(5):
        result = await limiter.check("test", "ip1", limit=5, window_seconds=60)
        assert result, f"Request {i + 1} should be allowed"
    over = await limiter.check("test", "ip1", limit=5, window_seconds=60)
    assert not over


@pytest.mark.asyncio
async def test_sliding_window_resets_after_window():
    limiter = SlidingWindowRateLimiter()
    window = 1
    for _ in range(3):
        await limiter.check("test", "ip2", limit=3, window_seconds=window)
    blocked = await limiter.check("test", "ip2", limit=3, window_seconds=window)
    assert not blocked
    await asyncio.sleep(window + 0.1)
    allowed = await limiter.check("test", "ip2", limit=3, window_seconds=window)
    assert allowed


@pytest.mark.asyncio
async def test_not_found_burst_locks_after_threshold():
    lockout = NotFoundBurstLockout(threshold=3, window_seconds=60, block_seconds=3600)
    for _ in range(3):
        await lockout.record_404("10.0.0.1")
    assert await lockout.is_blocked("10.0.0.1")


@pytest.mark.asyncio
async def test_not_found_burst_unblocks_after_period():
    lockout = NotFoundBurstLockout(threshold=3, window_seconds=60, block_seconds=1)
    for _ in range(3):
        await lockout.record_404("10.0.0.2")
    assert await lockout.is_blocked("10.0.0.2")
    await asyncio.sleep(1.1)
    assert not await lockout.is_blocked("10.0.0.2")


@pytest.mark.asyncio
async def test_not_found_burst_reset():
    lockout = NotFoundBurstLockout(threshold=3, window_seconds=60, block_seconds=3600)
    for _ in range(3):
        await lockout.record_404("10.0.0.3")
    assert await lockout.is_blocked("10.0.0.3")
    await lockout.reset("10.0.0.3")
    assert not await lockout.is_blocked("10.0.0.3")
    for _ in range(2):
        await lockout.record_404("10.0.0.3")
    assert not await lockout.is_blocked("10.0.0.3")


@pytest.mark.asyncio
async def test_sliding_window_no_unbounded_growth() -> None:
    rl = SlidingWindowRateLimiter()
    for i in range(1000):
        await rl.check("scope", f"id-{i}", limit=5, window_seconds=1)
    await asyncio.sleep(1.1)
    cleaned = await rl.cleanup_expired(max_age_seconds=1)
    assert cleaned > 0


@pytest.mark.asyncio
async def test_not_found_burst_no_growth_when_blocked() -> None:
    bl = NotFoundBurstLockout(threshold=3, window_seconds=10, block_seconds=2)
    for _ in range(1000):
        await bl.record_404("1.2.3.4")
    assert "1.2.3.4" not in bl._hits or len(bl._hits.get("1.2.3.4", [])) == 0
    assert await bl.is_blocked("1.2.3.4") is True
