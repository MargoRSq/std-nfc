import asyncio
import time
from collections import deque

from std_cards.config import settings


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, scope: str, identifier: str, limit: int, window_seconds: int) -> bool:
        """Return True if request is allowed (under limit), False if over."""
        key = (scope, identifier)
        cutoff = time.monotonic() - window_seconds
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = deque()
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                self._buckets[key] = bucket
                return False
            bucket.append(time.monotonic())
            self._buckets[key] = bucket
            return True

    async def cleanup_expired(self, max_age_seconds: int = 3600) -> int:
        """Освобождает память от пустых bucket'ов, возвращает count удалённых ключей."""
        cutoff = time.monotonic() - max_age_seconds
        async with self._lock:
            to_delete = []
            for key, bucket in self._buckets.items():
                while bucket and bucket[0] < cutoff:
                    bucket.popleft()
                if not bucket:
                    to_delete.append(key)
            for key in to_delete:
                del self._buckets[key]
            return len(to_delete)


class NotFoundBurstLockout:
    """Blocks an IP for block_seconds after threshold 404s within window_seconds."""

    def __init__(self, threshold: int, window_seconds: int, block_seconds: int) -> None:
        self._threshold = threshold
        self._window_seconds = window_seconds
        self._block_seconds = block_seconds
        self._hits: dict[str, deque[float]] = {}
        self._blocked_until: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def record_404(self, ip: str) -> None:
        now = time.monotonic()
        async with self._lock:
            if self._blocked_until.get(ip, 0) > now:
                self._blocked_until[ip] = max(self._blocked_until[ip], now + self._block_seconds)
                return

            bucket = self._hits.setdefault(ip, deque())
            cutoff = now - self._window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            bucket.append(now)
            if len(bucket) >= self._threshold:
                self._blocked_until[ip] = now + self._block_seconds
                self._hits.pop(ip, None)
            elif not bucket:
                self._hits.pop(ip, None)

    async def is_blocked(self, ip: str) -> bool:
        async with self._lock:
            until = self._blocked_until.get(ip)
            if until is None:
                return False
            if time.monotonic() >= until:
                del self._blocked_until[ip]
                return False
            return True

    async def reset(self, ip: str) -> None:
        async with self._lock:
            self._hits.pop(ip, None)
            self._blocked_until.pop(ip, None)


login_rate_limiter = SlidingWindowRateLimiter()
public_scan_limiter = SlidingWindowRateLimiter()
not_found_burst_lockout = NotFoundBurstLockout(
    threshold=settings.RATE_LIMIT.NOT_FOUND_BURST_THRESHOLD,
    window_seconds=settings.RATE_LIMIT.NOT_FOUND_BURST_WINDOW_SECONDS,
    block_seconds=settings.RATE_LIMIT.NOT_FOUND_BURST_BLOCK_SECONDS,
)
