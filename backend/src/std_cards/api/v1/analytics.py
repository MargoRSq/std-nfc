from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from std_cards.api.deps import AdminDep, AnalyticsServiceDep, AuditRepoDep, CardServiceDep
from std_cards.models.analytics import CardAnalytics, DashboardResponse, TopActiveUsersResponse
from std_cards.models.audit import AuditAction
from std_cards.services.analytics_report import build_card_report, build_dashboard_report

router = APIRouter(tags=["analytics"])


def _resolve_range(from_: date | None, to: date | None) -> tuple[datetime, datetime]:
    if from_ is None:
        from_ = (datetime.now(UTC) - timedelta(days=30)).date()
    if to is None:
        to = (datetime.now(UTC) + timedelta(days=1)).date()
    from_dt = datetime.combine(from_, datetime.min.time(), tzinfo=UTC)
    to_dt = datetime.combine(to, datetime.min.time(), tzinfo=UTC)
    return from_dt, to_dt


@router.get("/api/analytics/dashboard", response_model=DashboardResponse)
async def dashboard(
    user: AdminDep,
    service: AnalyticsServiceDep,
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
) -> DashboardResponse:
    if from_ is None:
        from_ = (datetime.now(UTC) - timedelta(days=30)).date()
    if to is None:
        to = (datetime.now(UTC) + timedelta(days=1)).date()
    from_dt = datetime.combine(from_, datetime.min.time(), tzinfo=UTC)
    to_dt = datetime.combine(to, datetime.min.time(), tzinfo=UTC)
    return await service.dashboard(from_dt, to_dt, user=user)


@router.get("/api/analytics/cards/{card_id}", response_model=CardAnalytics)
async def card_analytics(
    card_id: UUID,
    user: AdminDep,
    service: AnalyticsServiceDep,
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
) -> CardAnalytics:
    if from_ is None:
        from_ = (datetime.now(UTC) - timedelta(days=30)).date()
    if to is None:
        to = (datetime.now(UTC) + timedelta(days=1)).date()
    from_dt = datetime.combine(from_, datetime.min.time(), tzinfo=UTC)
    to_dt = datetime.combine(to, datetime.min.time(), tzinfo=UTC)
    return await service.card_analytics(card_id, from_dt, to_dt, user=user)


@router.get("/api/analytics/top-active", response_model=TopActiveUsersResponse)
async def top_active_users(
    user: AdminDep,
    service: AnalyticsServiceDep,
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> TopActiveUsersResponse:
    if from_ is None:
        from_ = (datetime.now(UTC) - timedelta(days=30)).date()
    if to is None:
        to = (datetime.now(UTC) + timedelta(days=1)).date()
    from_dt = datetime.combine(from_, datetime.min.time(), tzinfo=UTC)
    to_dt = datetime.combine(to, datetime.min.time(), tzinfo=UTC)
    return await service.top_active_users(from_dt, to_dt, page=page, page_size=page_size, user=user)


@router.get("/api/analytics/report.xlsx")
async def dashboard_report(
    user: AdminDep,
    service: AnalyticsServiceDep,
    audit: AuditRepoDep,
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
) -> StreamingResponse:
    from_dt, to_dt = _resolve_range(from_, to)
    dashboard_data = await service.dashboard(from_dt, to_dt, user=user)
    top_users = await service.top_active_users(
        from_dt, to_dt, page=1, page_size=100, user=user
    )
    content = build_dashboard_report(dashboard_data, top_users, from_dt, to_dt)
    filename = f"analytics-{from_dt.date().isoformat()}_{to_dt.date().isoformat()}.xlsx"
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.ANALYTICS_REPORT_EXPORT,
        entity_type="analytics",
        diff={"scope": "dashboard", "from": from_dt.date().isoformat(), "to": to_dt.date().isoformat()},
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.get("/api/analytics/cards/{card_id}/report.xlsx")
async def card_report(
    card_id: UUID,
    user: AdminDep,
    service: AnalyticsServiceDep,
    cards: CardServiceDep,
    audit: AuditRepoDep,
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
) -> StreamingResponse:
    from_dt, to_dt = _resolve_range(from_, to)
    analytics_data = await service.card_analytics(card_id, from_dt, to_dt, user=user)
    card = await cards.get(card_id, current_user=user)
    card_label = f"{card.last_name} {card.first_name} №{card.membership_no}".strip()
    content = build_card_report(analytics_data, from_dt, to_dt, card_label)
    filename = f"card-{card_id}-{from_dt.date().isoformat()}_{to_dt.date().isoformat()}.xlsx"
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.ANALYTICS_REPORT_EXPORT,
        entity_type="analytics",
        entity_id=str(card_id),
        diff={"scope": "card", "from": from_dt.date().isoformat(), "to": to_dt.date().isoformat()},
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
