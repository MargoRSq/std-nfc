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
        top_countries=[],
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
    assert "top_countries" in body
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
