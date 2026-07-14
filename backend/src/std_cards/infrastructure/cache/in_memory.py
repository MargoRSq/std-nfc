import asyncio
import time
from datetime import timedelta
from typing import Any

from std_cards.infrastructure.cache.interface import Cache


class InMemoryCache(Cache):
    """LRU-style кеш в памяти процесса.

    Подходит для одной replica (MVP std-cards). При scale на несколько replicas
    замени на RedisCache — интерфейс совместим.
    """

    def __init__(
        self, default_ttl: timedelta = timedelta(minutes=60), max_items: int = 10_000
    ) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl.total_seconds()
        self._max_items = max_items
        self._lock = asyncio.Lock()

    def _expired(self, expires_at: float) -> bool:
        return time.monotonic() > expires_at

    async def _evict_expired_unsafe(self) -> None:
        now = time.monotonic()
        for k in [k for k, (_, exp) in self._store.items() if exp <= now]:
            self._store.pop(k, None)

    async def get(self, cache_key: str) -> Any:
        async with self._lock:
            entry = self._store.get(cache_key)
            if not entry:
                return None
            value, exp = entry
            if self._expired(exp):
                self._store.pop(cache_key, None)
                return None
            return value

    async def put(self, cache_key: str, item: Any, ttl: timedelta | None = None) -> None:
        if item is None:
            return
        ttl_s = ttl.total_seconds() if ttl else self._default_ttl
        async with self._lock:
            if len(self._store) >= self._max_items:
                await self._evict_expired_unsafe()
                if len(self._store) >= self._max_items:
                    oldest_key = min(self._store.items(), key=lambda kv: kv[1][1])[0]
                    self._store.pop(oldest_key, None)
            self._store[cache_key] = (item, time.monotonic() + ttl_s)

    async def invalidate(self, cache_key: str) -> None:
        async with self._lock:
            self._store.pop(cache_key, None)

    async def bulk_invalidate(self, cache_keys: list[str]) -> None:
        async with self._lock:
            for k in cache_keys:
                self._store.pop(k, None)

    async def bulk_get(self, keys: list[str]) -> tuple[dict[str, Any], list[str]]:
        found: dict[str, Any] = {}
        missing: list[str] = []
        async with self._lock:
            now = time.monotonic()
            for k in keys:
                entry = self._store.get(k)
                if entry and entry[1] > now:
                    found[k] = entry[0]
                else:
                    if entry:
                        self._store.pop(k, None)
                    missing.append(k)
        return found, missing

    async def bulk_set(self, data: dict[str, Any], ttl: timedelta | None = None) -> None:
        ttl_s = ttl.total_seconds() if ttl else self._default_ttl
        async with self._lock:
            now = time.monotonic()
            for k, v in data.items():
                if v is None:
                    continue
                self._store[k] = (v, now + ttl_s)
            if len(self._store) > self._max_items:
                await self._evict_expired_unsafe()
                while len(self._store) > self._max_items:
                    oldest_key = min(self._store.items(), key=lambda kv: kv[1][1])[0]
                    self._store.pop(oldest_key, None)
