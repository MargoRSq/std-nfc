from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from std_cards.config import settings


def make_engine() -> AsyncEngine:
    return create_async_engine(
        settings.effective_db_url,
        echo=False,
        pool_pre_ping=settings.POSTGRES.POOL_PRE_PING,
        pool_size=settings.POSTGRES.POOL_SIZE,
        max_overflow=settings.POSTGRES.POOL_MAX_OVERFLOW,
        pool_recycle=settings.POSTGRES.POOL_RECYCLE_SECONDS,
    )


class Session:
    """Async context manager поверх AsyncConnection с auto-commit/rollback.

    Используется repositories напрямую (не через AsyncSession ORM).
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self.conn: AsyncConnection | None = None

    async def __aenter__(self) -> AsyncConnection:
        self.conn = await self._engine.connect()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.conn is None:
            return
        try:
            if exc_val is not None:
                await self.conn.rollback()
            else:
                await self.conn.commit()
        finally:
            await self.conn.close()


class SessionMaker:
    """Producer Session-объектов поверх единого engine.

    Без master/replica split — для std-cards 50К+ карточек одного Postgres достаточно.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    def session(self, query_type: str = "write") -> Session:
        # query_type принимаем для совместимости с tms-style API.
        # В текущей реализации игнорируется (нет replica), но даёт hook для метрик.
        del query_type
        return Session(self.engine)


_engine: AsyncEngine | None = None
_session_maker: SessionMaker | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def get_session_maker() -> SessionMaker:
    global _session_maker
    if _session_maker is None:
        _session_maker = SessionMaker(get_engine())
    return _session_maker


async def dispose_engine() -> None:
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_maker = None


async def get_db_connection() -> AsyncIterator[AsyncConnection]:
    """FastAPI Depends для inline получения AsyncConnection.

    Большинство endpoints должны брать репозиторий через Depends(get_X_repo),
    а не connection напрямую. Эта функция — escape hatch для системных endpoints (/readyz и т.п.).
    """
    sm = get_session_maker()
    async with sm.session() as conn:
        yield conn
