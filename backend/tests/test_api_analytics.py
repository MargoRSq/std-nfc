from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.models.analytics import DashboardKpi, DashboardResponse
from std_cards.models.auth import UserCreate, UserRole


@pytest.fixture
async def admin_token(client: AsyncClient, user_repo):
    pw = "analAdmin#1"
    await user_repo.create(
        UserCreate(email="anal_admin@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    r = await client.post("/api/auth/login", json={"email": "anal_admin@x.com", "password": pw})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _mock_dashboard() -> DashboardResponse:
    return DashboardResponse(
        kpi=DashboardKpi(total_scans=100, last_30d_scans=30, unique_cards=5, active_members=5),
        by_day=[],
        top_regions=[],
        top_devices=[],
        top_cards=[],
    )


async def test_dashboard_requires_auth(client: AsyncClient):
    r = await client.get("/api/analytics/dashboard")
    assert r.status_code == 401


async def test_dashboard_returns_structure(client: AsyncClient, auth_headers):
    mock_svc = AsyncMock()
    mock_svc.dashboard = AsyncMock(return_value=_mock_dashboard())

    with patch("std_cards.api.deps.get_analytics_service", return_value=mock_svc):
        r = await client.get("/api/analytics/dashboard", headers=auth_headers)

    assert r.status_code == 200
    body = r.json()
    assert "kpi" in body
    assert "by_day" in body
    assert "top_regions" in body
    assert "top_devices" in body
    assert "top_cards" in body


async def test_dashboard_with_date_params(client: AsyncClient, auth_headers):
    mock_svc = AsyncMock()
    mock_svc.dashboard = AsyncMock(return_value=_mock_dashboard())

    with patch("std_cards.api.deps.get_analytics_service", return_value=mock_svc):
        r = await client.get(
            "/api/analytics/dashboard?from=2026-04-01&to=2026-05-01",
            headers=auth_headers,
        )

    assert r.status_code == 200


async def test_card_analytics_requires_auth(client: AsyncClient):
    from uuid import uuid4

    card_id = uuid4()
    r = await client.get(f"/api/analytics/cards/{card_id}")
    assert r.status_code == 401


def test_resolve_range_includes_whole_to_day():
    """`to` включительно: репозиторий фильтрует ts < to_dt, поэтому конец — начало
    следующего дня. Иначе сегодняшние сканы не попадали в дашборд."""
    from datetime import UTC, date, datetime

    from std_cards.api.v1.analytics import _resolve_range

    from_dt, to_dt = _resolve_range(date(2026, 7, 1), date(2026, 7, 27))
    assert from_dt == datetime(2026, 7, 1, tzinfo=UTC)
    assert to_dt == datetime(2026, 7, 28, tzinfo=UTC)


async def test_dashboard_counts_scans_of_the_to_day(client: AsyncClient, user_repo, session_maker):
    """Скан «сегодня» виден при to=сегодня — из-за старой границы диапазона
    «Всего сканирований» показывало 0 при живых скан-событиях."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from std_cards.infrastructure.repositories.card_repo import CardRepository
    from std_cards.infrastructure.repositories.scan_repo import ScanEventRepository
    from std_cards.models.card import CardCreate

    # super_admin: у обычного админа ACL режет чужие карточки и скан не попадёт в дашборд
    pw = "scanSuper#1"
    user = await user_repo.create(
        UserCreate(
            email="scan_super@x.com", password_hash=hash_password(pw), role=UserRole.SUPER_ADMIN
        )
    )
    login = await client.post("/api/auth/login", json={"email": "scan_super@x.com", "password": pw})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    card = await CardRepository(session_maker).create(
        CardCreate(
            last_name="Скан",
            first_name="Тест",
            membership_no=f"MBR-{uuid4().hex[:8]}",
            category_id=1,
        ),
        slug=f"sc{uuid4().hex[:6]}",
        created_by=user.id,
    )
    await ScanEventRepository(session_maker).insert_batch(
        [{"card_id": card.id, "ts": datetime.now(UTC), "is_bot": False}]
    )
    today = datetime.now(UTC).date().isoformat()
    r = await client.get(f"/api/analytics/dashboard?from={today}&to={today}", headers=headers)
    assert r.status_code == 200
    assert r.json()["kpi"]["total_scans"] >= 1
