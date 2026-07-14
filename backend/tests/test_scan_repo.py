from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.scan_repo import ScanEventRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole
from std_cards.models.card import CardCreate


async def _make_user(session_maker):
    repo = UserRepository(session_maker)
    return await repo.create(
        UserCreate(email=f"u{uuid4().hex[:6]}@x.com", password_hash="h", role=UserRole.ADMIN)
    )


async def _make_card(session_maker, user_id, slug=None):
    repo = CardRepository(session_maker)
    slug = slug or f"sl{uuid4().hex[:6]}"
    return await repo.create(
        CardCreate(last_name="Тест", first_name="Иван", membership_no="MBR-01", category_id=1),
        slug=slug,
        created_by=user_id,
    )


@pytest.fixture
def scan_repo(session_maker) -> ScanEventRepository:
    return ScanEventRepository(session_maker)


async def test_insert_batch_and_total_scans(scan_repo, session_maker):
    user = await _make_user(session_maker)
    card = await _make_card(session_maker, user.id)

    now = datetime.now(UTC)
    events = [
        {"card_id": card.id, "ts": now - timedelta(hours=i), "is_bot": False} for i in range(5)
    ]
    n = await scan_repo.insert_batch(events)
    assert n == 5

    total = await scan_repo.total_scans()
    assert total >= 5


async def test_total_scans_with_time_filter(scan_repo, session_maker):
    user = await _make_user(session_maker)
    card = await _make_card(session_maker, user.id)

    now = datetime.now(UTC)
    earlier = now - timedelta(hours=3)
    recent = now - timedelta(hours=1)

    await scan_repo.insert_batch(
        [
            {"card_id": card.id, "ts": earlier, "is_bot": False},
            {"card_id": card.id, "ts": recent, "is_bot": False},
        ]
    )

    from_dt = now - timedelta(hours=2)
    to_dt = now + timedelta(days=1)
    count = await scan_repo.total_scans(from_dt=from_dt, to_dt=to_dt)
    assert count >= 1

    all_count = await scan_repo.total_scans()
    assert all_count >= 2


async def test_by_day(scan_repo, session_maker):
    user = await _make_user(session_maker)
    card = await _make_card(session_maker, user.id)

    now = datetime.now(UTC)
    events = [
        {"card_id": card.id, "ts": now - timedelta(hours=i), "is_bot": False} for i in range(3)
    ]
    await scan_repo.insert_batch(events)

    from_dt = now - timedelta(days=2)
    to_dt = now + timedelta(days=1)
    rows = await scan_repo.by_day(from_dt=from_dt, to_dt=to_dt)
    assert len(rows) >= 1
    assert "day" in rows[0]
    assert "count" in rows[0]


async def test_top_countries(scan_repo, session_maker):
    user = await _make_user(session_maker)
    card = await _make_card(session_maker, user.id)

    now = datetime.now(UTC)
    events = [
        {
            "card_id": card.id,
            "ts": now - timedelta(minutes=i),
            "is_bot": False,
            "country_code": "RU",
        }
        for i in range(3)
    ] + [
        {
            "card_id": card.id,
            "ts": now - timedelta(minutes=20),
            "is_bot": False,
            "country_code": "US",
        }
    ]
    await scan_repo.insert_batch(events)

    from_dt = now - timedelta(days=1)
    to_dt = now + timedelta(days=1)
    rows = await scan_repo.top_countries(from_dt=from_dt, to_dt=to_dt, limit=5)
    codes = [r["country_code"] for r in rows]
    assert "RU" in codes
    assert rows[0]["country_code"] == "RU"


async def test_top_cards(scan_repo, session_maker):
    user = await _make_user(session_maker)
    card1 = await _make_card(session_maker, user.id)
    card2 = await _make_card(session_maker, user.id)

    now = datetime.now(UTC)
    await scan_repo.insert_batch(
        [{"card_id": card1.id, "ts": now - timedelta(minutes=i), "is_bot": False} for i in range(5)]
        + [
            {"card_id": card2.id, "ts": now - timedelta(minutes=i), "is_bot": False}
            for i in range(2)
        ]
    )

    from_dt = now - timedelta(days=1)
    to_dt = now + timedelta(days=1)
    rows = await scan_repo.top_cards(from_dt=from_dt, to_dt=to_dt, limit=10)
    assert len(rows) >= 2
    assert rows[0]["card_id"] == card1.id
    assert rows[0]["scans"] == 5


async def test_unique_cards(scan_repo, session_maker):
    user = await _make_user(session_maker)
    card1 = await _make_card(session_maker, user.id)
    card2 = await _make_card(session_maker, user.id)

    now = datetime.now(UTC)
    await scan_repo.insert_batch(
        [
            {"card_id": card1.id, "ts": now, "is_bot": False},
            {"card_id": card1.id, "ts": now - timedelta(minutes=1), "is_bot": False},
            {"card_id": card2.id, "ts": now - timedelta(minutes=2), "is_bot": False},
        ]
    )

    from_dt = now - timedelta(days=1)
    to_dt = now + timedelta(days=1)
    unique = await scan_repo.unique_cards(from_dt=from_dt, to_dt=to_dt)
    assert unique >= 2


async def test_last_scan(scan_repo, session_maker):
    user = await _make_user(session_maker)
    card = await _make_card(session_maker, user.id)

    now = datetime.now(UTC)
    await scan_repo.insert_batch(
        [
            {"card_id": card.id, "ts": now - timedelta(hours=2), "is_bot": False},
            {"card_id": card.id, "ts": now - timedelta(hours=1), "is_bot": False},
        ]
    )

    last = await scan_repo.last_scan(card.id)
    assert last is not None
    assert abs((last - (now - timedelta(hours=1))).total_seconds()) < 5


async def test_insert_batch_empty(scan_repo):
    n = await scan_repo.insert_batch([])
    assert n == 0
