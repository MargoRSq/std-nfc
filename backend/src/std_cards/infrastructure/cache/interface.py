from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any
from uuid import UUID


class Cache(ABC):
    """Кеш-абстракция. Реализации: InMemoryCache (MVP), RedisCache (позже)."""

    @abstractmethod
    async def get(self, cache_key: str) -> Any: ...

    @abstractmethod
    async def put(self, cache_key: str, item: Any, ttl: timedelta | None = None) -> None: ...

    @abstractmethod
    async def invalidate(self, cache_key: str) -> None: ...

    @abstractmethod
    async def bulk_invalidate(self, cache_keys: list[str]) -> None: ...

    @abstractmethod
    async def bulk_get(self, keys: list[str]) -> tuple[dict[str, Any], list[str]]:
        """Returns (found, missing). `found` — `{key: value}` для попавших, `missing` — list ключей не найденных."""

    @abstractmethod
    async def bulk_set(self, data: dict[str, Any], ttl: timedelta | None = None) -> None: ...

    @staticmethod
    def make_key(
        table: str,
        service: str | None = None,
        model: str | None = None,
        uid: UUID | str | int | None = None,
    ) -> str:
        parts = [p for p in (service, table, model, str(uid) if uid is not None else None) if p]
        return ":".join(parts)
