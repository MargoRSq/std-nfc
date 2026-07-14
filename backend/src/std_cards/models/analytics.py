from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardKpi(BaseModel):
    total_scans: int
    last_30d_scans: int
    unique_cards: int
    active_members: int


class TimelinePoint(BaseModel):
    day: date
    count: int


class RegionStats(BaseModel):
    """Top regions for scans. Prefers city, falls back to country code if city unknown."""

    region: str
    count: int


class DeviceStats(BaseModel):
    device_type: str
    count: int


class TopCard(BaseModel):
    card_id: UUID
    last_name: str
    first_name: str
    membership_no: str
    scans: int


class TopActiveUser(BaseModel):
    card_id: UUID
    last_name: str
    first_name: str
    middle_name: str | None = None
    category_name: str | None = None
    membership_no: str
    scans: int
    top_region: str | None = None
    top_device: str | None = None


class TopActiveUsersResponse(BaseModel):
    items: list[TopActiveUser]
    total: int
    page: int
    page_size: int


class DashboardResponse(BaseModel):
    kpi: DashboardKpi
    by_day: list[TimelinePoint]
    top_regions: list[RegionStats]
    top_devices: list[DeviceStats]
    top_cards: list[TopCard]


class CardAnalytics(BaseModel):
    card_id: UUID
    total_scans: int
    last_scan: datetime | None
    by_day: list[TimelinePoint]
    by_region: list[RegionStats]
    by_device: list[DeviceStats]


class ScanEvent(BaseModel):
    card_id: UUID
    ts: datetime
    ip: str | None = None
    user_agent: str | None = None
    referer: str | None = None
