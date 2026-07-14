import logging
from typing import Any

from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql import Delete, Insert, Select, Update
from sqlalchemy.sql.selectable import CTE

from std_cards.config import settings
from std_cards.db.session import SessionMaker

logger = logging.getLogger(__name__)

_STALE_CONNECTION_MESSAGES = (
    "server closed the connection",
    "connection is closed",
    "connection already closed",
    "lost connection",
    "broken pipe",
)


class BaseRepository:
    """Базовый репозиторий с авто-управлением соединением и retry.

    Паттерн скопирован из tms-recommendations:
    - `ctx_wrap(query, conn=None)` — выполняет query, оптом detect read/write,
      берёт connection из session_maker если не передан, на stale connection
      делает один retry.
    - `conn` параметр — для участия в external transaction.
    - `local_debug` — печатает compiled SQL с literal_binds.
    """

    def __init__(self, session_maker: SessionMaker) -> None:
        self.session_maker = session_maker

    @staticmethod
    def _is_select_write(query: Select) -> bool:
        for item in query.get_final_froms():
            if isinstance(item, CTE):
                element = item.element
                if isinstance(element, Insert | Update | Delete):
                    return True
                if isinstance(element, Select) and BaseRepository._is_select_write(element):
                    return True
        return False

    @classmethod
    def _get_query_type(cls, query: Any) -> str:
        if isinstance(query, Insert | Update | Delete):
            return "write"
        if isinstance(query, Select):
            return "write" if cls._is_select_write(query) else "read"
        return "write"

    @staticmethod
    def _is_stale_connection_error(exc: BaseException) -> bool:
        msg = (getattr(exc, "message", None) or str(exc)).lower()
        return any(s in msg for s in _STALE_CONNECTION_MESSAGES)

    @staticmethod
    def _maybe_log_query(query: Any, local_debug: bool) -> None:
        if not (settings.DEBUG or local_debug):
            return
        try:
            compiled = query.compile(
                dialect=dialect(),
                compile_kwargs={"literal_binds": settings.LITERAL_BINDS},
            )
            logger.info("SQL: %s", compiled)
        except Exception:
            logger.exception("Failed to compile query for debug log")

    async def ctx_wrap(
        self,
        query: Any,
        conn: AsyncConnection | None = None,
        local_debug: bool = False,
    ) -> Any:
        self._maybe_log_query(query, local_debug)
        if conn is not None:
            return await conn.execute(query)

        query_type = self._get_query_type(query)
        try:
            async with self.session_maker.session(query_type=query_type) as new_conn:
                return await new_conn.execute(query)
        except OperationalError as exc:
            if not self._is_stale_connection_error(exc):
                raise
            logger.warning("Stale connection, retrying once", exc_info=True)
        async with self.session_maker.session(query_type=query_type) as retry_conn:
            return await retry_conn.execute(query)

    async def ctx_wrap_with_data(
        self,
        query: Any,
        data: Any,
        conn: AsyncConnection | None = None,
        local_debug: bool = False,
    ) -> Any:
        self._maybe_log_query(query, local_debug)
        if conn is not None:
            return await conn.execute(query, data)

        query_type = self._get_query_type(query)
        try:
            async with self.session_maker.session(query_type=query_type) as new_conn:
                return await new_conn.execute(query, data)
        except OperationalError as exc:
            if not self._is_stale_connection_error(exc):
                raise
            logger.warning("Stale connection (with_data), retrying once", exc_info=True)
        async with self.session_maker.session(query_type=query_type) as retry_conn:
            return await retry_conn.execute(query, data)
