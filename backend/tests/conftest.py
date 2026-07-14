from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from std_cards.config import settings
from std_cards.core.ratelimit import not_found_burst_lockout, public_scan_limiter
from std_cards.db.session import SessionMaker
from std_cards.infrastructure.repositories import CategoryRepository, UserRepository
from std_cards.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture(scope="session")
async def session_maker():
    """Session-scoped engine with NullPool — one event loop for all tests."""
    engine = create_async_engine(settings.effective_db_url, echo=False, poolclass=NullPool)
    sm = SessionMaker(engine)
    yield sm
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_db(session_maker):
    try:
        async with session_maker.session() as conn:
            await conn.execute(
                text(
                    "TRUNCATE audit_log, admin_card_groups, import_jobs, cards, templates, users, categories"
                    " RESTART IDENTITY CASCADE"
                )
            )
            await conn.execute(
                text("""
                INSERT INTO categories (code, name_ru, order_idx) VALUES
                    ('platinum', 'Платиновые', 1),
                    ('gold', 'Золотые', 2),
                    ('silver', 'Серебряные', 3),
                    ('bronze', 'Бронзовые', 4)
            """)
            )
    except Exception:
        pass

    async with not_found_burst_lockout._lock:
        not_found_burst_lockout._hits.clear()
        not_found_burst_lockout._blocked_until.clear()
    async with public_scan_limiter._lock:
        public_scan_limiter._buckets.clear()
    return


@pytest.fixture
def user_repo(session_maker) -> UserRepository:
    return UserRepository(session_maker)


@pytest.fixture
def category_repo(session_maker) -> CategoryRepository:
    return CategoryRepository(session_maker)
