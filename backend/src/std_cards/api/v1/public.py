import asyncio
import logging
import re
from urllib.parse import urlparse

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from std_cards.api.deps import (
    AdminDep,
    CardMessageRepoDep,
    CardServiceDep,
    FeedbackRepoDep,
    ScanServiceDep,
)
from std_cards.config import settings
from std_cards.core.color import contrast_palette
from std_cards.core.exceptions import NotFoundError, RateLimitedError
from std_cards.core.net import client_ip
from std_cards.core.ratelimit import not_found_burst_lockout, public_scan_limiter
from std_cards.core.templating import render
from std_cards.core.translations import get_translations
from std_cards.models.feedback import FeedbackDB
from std_cards.services.og_service import render_card_og

router = APIRouter(tags=["public"])

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> None:
    """Fire-and-forget a coroutine, holding a strong reference (so the event
    loop doesn't GC it mid-flight) and logging any exception it raises."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    def _log_exc(t: asyncio.Task) -> None:
        if not t.cancelled() and t.exception() is not None:
            logger.warning("background task failed", exc_info=t.exception())

    task.add_done_callback(_log_exc)


NOINDEX_HEADERS: dict[str, str] = {
    "Cache-Control": "private, no-store, max-age=0",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data: blob:; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "frame-ancestors 'none';"
    ),
}


def _get_ip(request: Request) -> str:
    return client_ip(request) or "unknown"


def _html_error(status: int, message_key: str) -> Response:
    t = get_translations()
    message = t.get(message_key, message_key)
    html = render("error.html", status=status, message=message)
    return HTMLResponse(content=html, status_code=status, headers=NOINDEX_HEADERS)


_HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _safe_bg(card_dict: dict) -> tuple[dict, str]:
    """Return defensively-validated card_dict and bg_for_palette colour."""
    fallback = "#1F1E5E"
    bg_kind = card_dict.get("bg_kind")
    bg_color = card_dict.get("bg_color") or fallback
    if not _HEX_PATTERN.match(bg_color):
        bg_color = fallback
    card_dict["bg_color"] = bg_color
    bg_for_palette = bg_color

    if bg_kind == "gradient":
        g = card_dict.get("bg_gradient") or {}
        from_c = g.get("from") or g.get("start") or fallback
        to_c = g.get("to") or g.get("end") or "#798BFF"
        if not _HEX_PATTERN.match(from_c):
            from_c = fallback
        if not _HEX_PATTERN.match(to_c):
            to_c = "#798BFF"
        angle = g.get("angle", 180)
        try:
            angle = int(angle)
            if angle < 0 or angle > 360:
                angle = 180
        except (TypeError, ValueError):
            angle = 180
        card_dict["bg_gradient"] = {
            "from": from_c,
            "to": to_c,
            "start": from_c,
            "end": to_c,
            "angle": angle,
        }
        bg_for_palette = from_c
    elif bg_kind != "solid":
        card_dict["bg_kind"] = "solid"

    return card_dict, bg_for_palette


def _is_internal_referer(request: Request) -> bool:
    """Return True only if user came from an admin page on the same host.

    Self-references (e.g. reloading the public page) MUST NOT trigger the
    close-X — otherwise it appears spuriously on in-page navigation.
    """
    referer = request.headers.get("referer", "")
    if not referer:
        return False
    host = request.headers.get("host", "")
    if not host or host not in referer:
        return False
    try:
        path = urlparse(referer).path
    except ValueError:
        return False
    return path.startswith("/admin/")


@router.get("/c/{slug}", include_in_schema=False)
async def public_card(
    slug: str,
    request: Request,
    card_service: CardServiceDep,
    scan_service: ScanServiceDep,
    message_repo: CardMessageRepoDep,
) -> Response:
    ip = _get_ip(request)

    if await not_found_burst_lockout.is_blocked(ip):
        return _html_error(429, "rate_limited")

    ok = await public_scan_limiter.check(
        scope="public_scan",
        identifier=ip,
        limit=settings.RATE_LIMIT.PUBLIC_SCAN_PER_MIN,
        window_seconds=60,
    )
    if not ok:
        return _html_error(429, "rate_limited")

    card = await card_service.cards.get_by_slug(slug)
    if card is None:
        await not_found_burst_lockout.record_404(ip)
        return _html_error(404, "card_not_found")

    if not card.is_active:
        latest_msg_inactive = await message_repo.get_latest_active_for_card(card.id)
        if latest_msg_inactive is not None:
            inactive_dict, _ = _safe_bg(card.model_dump())
            html = render(
                "invalid_card.html",
                card=inactive_dict,
                message={
                    "text": latest_msg_inactive.text,
                    "image_key": latest_msg_inactive.image_key,
                },
            )
            return HTMLResponse(content=html, status_code=200, headers=NOINDEX_HEADERS)
        return _html_error(410, "card_invalid")

    await not_found_burst_lockout.reset(ip)

    ua = request.headers.get("user-agent")
    referer = request.headers.get("referer")
    _spawn(scan_service.publish_scan(card.id, ip, ua, referer))
    _spawn(card_service.cards.update_last_opened(card.id))

    card_dict, bg_for_palette = _safe_bg(card.model_dump())
    palette = contrast_palette(bg_for_palette)

    latest_msg = await message_repo.get_latest_active_for_card(card.id)
    message = (
        {
            "text": latest_msg.text,
            "image_key": latest_msg.image_key,
            "created_at": latest_msg.created_at.isoformat(),
        }
        if latest_msg is not None
        else None
    )

    show_close = _is_internal_referer(request)

    updated_unix = int(card.updated_at.timestamp()) if card.updated_at else 0

    html = render(
        "card.html",
        card=card_dict,
        slug=slug,
        palette=palette,
        message=message,
        show_close=show_close,
        updated_unix=updated_unix,
        base_url=settings.PUBLIC_CARD_BASE_URL.rstrip("/"),
    )
    return HTMLResponse(content=html, status_code=200, headers=NOINDEX_HEADERS)


@router.get("/c/{slug}/og.png", include_in_schema=False)
async def public_card_og(
    slug: str,
    request: Request,
    card_service: CardServiceDep,
) -> Response:
    """Render personalized OG image for public card; fallback to default on miss."""
    ip = _get_ip(request)
    # OG render is expensive (MinIO fetch + pixel work); throttle to defeat
    # ?v=N ETag-bypass hammering. Fall back to the default image when limited.
    if await not_found_burst_lockout.is_blocked(ip) or not await public_scan_limiter.check(
        scope="og",
        identifier=ip,
        limit=settings.RATE_LIMIT.PUBLIC_SCAN_PER_MIN,
        window_seconds=60,
    ):
        return Response(status_code=302, headers={"Location": "/og-default.png"})

    card = await card_service.cards.get_by_slug(slug)
    if card is None or not card.is_active:
        if card is None:
            await not_found_burst_lockout.record_404(ip)
        return Response(status_code=302, headers={"Location": "/og-default.png"})

    updated_unix = int(card.updated_at.timestamp()) if card.updated_at else 0
    etag = f'W/"{slug}-{updated_unix}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})

    photo_bytes: bytes | None = None
    if card.photo_key:
        try:
            from std_cards.infrastructure.minio import get_minio

            photo_bytes = await get_minio().download(settings.MINIO.BUCKET_CARDS, card.photo_key)
        except Exception:
            photo_bytes = None

    card_dict, _ = _safe_bg(card.model_dump())
    png = await asyncio.to_thread(render_card_og, card_dict, photo_bytes)
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "ETag": etag,
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@router.get("/c/{slug}/contact", include_in_schema=False)
async def public_contact_form(
    slug: str,
    card_service: CardServiceDep,
) -> Response:
    card = await card_service.cards.get_by_slug(slug)
    if card is None:
        return _html_error(404, "card_not_found")
    if not card.feedback_form_enabled:
        return _html_error(403, "feedback_unavailable")
    card_dict, _ = _safe_bg(card.model_dump())
    html = render("contact.html", slug=slug, card=card_dict)
    return HTMLResponse(content=html, headers=NOINDEX_HEADERS)


class FeedbackBody(BaseModel):
    name: str
    contact: str
    message: str


@router.post("/api/public/cards/{slug}/feedback", status_code=204, include_in_schema=False)
async def feedback(
    slug: str,
    body: FeedbackBody,
    request: Request,
    card_service: CardServiceDep,
    feedback_repo: FeedbackRepoDep,
    scan_service: ScanServiceDep,
) -> Response:
    ip = _get_ip(request)
    ok = await public_scan_limiter.check(
        scope="feedback", identifier=ip, limit=10, window_seconds=3600
    )
    if not ok:
        raise RateLimitedError()
    card = await card_service.cards.get_by_slug(slug)
    if card is None or not card.is_active:
        raise NotFoundError()

    ua = request.headers.get("user-agent")
    await feedback_repo.create(
        card_id=card.id,
        name=body.name,
        contact=body.contact,
        message=body.message,
        ip=ip,
        user_agent=ua,
    )

    if scan_service.nats is not None:
        _spawn(
            scan_service.nats.publish(
                subject="cards.feedback.received",
                message_type="feedback_received",
                payload={"card_id": str(card.id), "slug": slug},
            )
        )

    return Response(status_code=204)


class FeedbackList(BaseModel):
    items: list[FeedbackDB]
    total: int
    page: int
    page_size: int


@router.get("/api/cards/{id}/feedback")
async def list_card_feedback(
    id: str,
    _user: AdminDep,
    feedback_repo: FeedbackRepoDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> FeedbackList:
    from uuid import UUID

    card_id = UUID(id)
    items, total = await feedback_repo.list_for_card(card_id, page=page, page_size=page_size)
    return FeedbackList(items=items, total=total, page=page, page_size=page_size)
