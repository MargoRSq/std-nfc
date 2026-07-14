import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from std_cards.models.analytics import (
    CardAnalytics,
    DashboardResponse,
)
from std_cards.services.analytics_service import AnalyticsService


def _make_scan_repo(
    *,
    total=0,
    last30=0,
    by_day=None,
    regions=None,
    devices=None,
    top_cards=None,
    unique=0,
    last_scan=None,
    card_total=0,
    by_region=None,
    by_device=None,
):
    repo = AsyncMock()
    repo.total_scans = AsyncMock(
        side_effect=lambda from_dt=None, to_dt=None: total if from_dt is None else last30
    )
    repo.by_day = AsyncMock(return_value=by_day or [])
    repo.top_regions = AsyncMock(return_value=regions or [])
    repo.top_devices = AsyncMock(return_value=devices or [])
    repo.top_cards = AsyncMock(return_value=top_cards or [])
    repo.unique_cards = AsyncMock(return_value=unique)
    repo.last_scan = AsyncMock(return_value=last_scan)
    repo.card_total_scans = AsyncMock(return_value=card_total)
    repo.by_country_for_card = AsyncMock(return_value=by_region or [])
    repo.by_device_for_card = AsyncMock(return_value=by_device or [])
    return repo


async def test_dashboard_returns_response():
    repo = _make_scan_repo(
        total=100,
        last30=30,
        unique=5,
        by_day=[{"day": datetime.now(UTC).date(), "count": 10}],
        regions=[{"region": "RU", "count": 50}],
        devices=[{"device_type": "mobile", "count": 60}],
        top_cards=[
            {
                "card_id": uuid4(),
                "last_name": "Иванов",
                "first_name": "Иван",
                "membership_no": "001",
                "scans": 20,
            }
        ],
    )
    svc = AnalyticsService(repo, AsyncMock())

    now = datetime.now(UTC)
    result = await svc.dashboard(now - timedelta(days=30), now)

    assert isinstance(result, DashboardResponse)
    assert result.kpi.total_scans == 100
    assert result.kpi.unique_cards == 5
    assert len(result.by_day) == 1
    assert result.by_day[0].count == 10
    assert result.top_regions[0].region == "RU"
    assert result.top_devices[0].device_type == "mobile"
    assert result.top_cards[0].last_name == "Иванов"


async def test_dashboard_caching():
    repo = _make_scan_repo(total=42, unique=3)
    svc = AnalyticsService(repo, AsyncMock())

    now = datetime.now(UTC)
    from_dt = now - timedelta(days=7)
    to_dt = now

    result1 = await svc.dashboard(from_dt, to_dt)
    result2 = await svc.dashboard(from_dt, to_dt)

    assert result1 is result2
    assert repo.total_scans.call_count == 2


async def test_dashboard_cache_expires():
    repo = _make_scan_repo(total=10, unique=1)
    svc = AnalyticsService(repo, AsyncMock())

    now = datetime.now(UTC)
    from_dt = now - timedelta(days=1)
    to_dt = now

    await svc.dashboard(from_dt, to_dt)

    cache_key = f"dash:{from_dt.isoformat()}:{to_dt.isoformat()}"
    svc._cache[cache_key] = (time.monotonic() - 1, svc._cache[cache_key][1])

    await svc.dashboard(from_dt, to_dt)
    assert repo.total_scans.call_count == 4


async def test_card_analytics():
    card_id = uuid4()
    now = datetime.now(UTC)

    repo = _make_scan_repo(
        card_total=15,
        last_scan=now - timedelta(hours=2),
        by_day=[{"day": now.date(), "count": 5}],
        by_region=[{"region": "RU", "count": 10}],
        by_device=[{"device_type": "desktop", "count": 15}],
    )
    svc = AnalyticsService(repo, AsyncMock())

    result = await svc.card_analytics(card_id, now - timedelta(days=30), now)

    assert isinstance(result, CardAnalytics)
    assert result.card_id == card_id
    assert result.total_scans == 15
    assert result.last_scan is not None
    assert result.by_region[0].region == "RU"
    assert result.by_device[0].device_type == "desktop"
