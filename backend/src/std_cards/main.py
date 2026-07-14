import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sqlalchemy import text

from std_cards.api.exception_handlers import register_exception_handlers
from std_cards.api.middleware import SecurityHeadersMiddleware
from std_cards.api.v1.admins import router as admins_router
from std_cards.api.v1.analytics import router as analytics_router
from std_cards.api.v1.auth import router as auth_router
from std_cards.api.v1.card_messages import router as card_messages_router
from std_cards.api.v1.cards import router as cards_router
from std_cards.api.v1.categories import router as categories_router
from std_cards.api.v1.imports import router as imports_router
from std_cards.api.v1.label_presets import router as label_presets_router
from std_cards.api.v1.media import router as media_router
from std_cards.api.v1.public import router as public_router
from std_cards.api.v1.templates import router as templates_router
from std_cards.config import settings
from std_cards.core.metrics import setup_metrics
from std_cards.core.nats.client import NatsClient
from std_cards.core.nats.publisher import NatsPublisher
from std_cards.core.ratelimit import login_rate_limiter, public_scan_limiter
from std_cards.db.session import dispose_engine, get_engine

if settings.SENTRY.DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY.DSN,
        environment=settings.SENTRY.ENVIRONMENT or settings.ENVIRONMENT,
        traces_sample_rate=0.1 if settings.is_dev else 0.05,
        integrations=[FastApiIntegration()],
    )

logger = logging.getLogger(__name__)

_nats_client: NatsClient | None = None

MAINTENANCE_INTERVAL_SECONDS = 3600


async def _evict_rate_limit_buckets() -> None:
    """Evict expired in-memory rate-limit buckets. Per-process and API-only —
    DB-side maintenance (partitions, expired auth rows) runs in the worker."""
    await login_rate_limiter.cleanup_expired()
    await public_scan_limiter.cleanup_expired()


async def _maintenance_loop() -> None:
    while True:
        await asyncio.sleep(MAINTENANCE_INTERVAL_SECONDS)
        try:
            await _evict_rate_limit_buckets()
        except Exception:
            logger.exception("rate-limit bucket eviction failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _nats_client
    get_engine()

    try:
        await _evict_rate_limit_buckets()
    except Exception:
        logger.exception("initial rate-limit eviction failed")
    maintenance_task = asyncio.create_task(_maintenance_loop(), name="rl-eviction")

    if settings.NATS.URL:
        try:
            _nats_client = NatsClient(settings.SERVICE_NAME)
            await _nats_client.connect(settings.NATS.URL)
            await _nats_client.ensure_stream(
                "CARDS_IMPORT",
                subjects=["cards.import.process", "cards.import.progress.>"],
            )
            await _nats_client.ensure_stream(
                "CARDS_SCAN",
                subjects=["cards.scan.recorded", "cards.feedback.received"],
            )
            app.state.nats = _nats_client
            app.state.nats_publisher = NatsPublisher(_nats_client)
        except Exception as exc:
            logger.exception("NATS connect failed: %s", exc)
            _nats_client = None

    yield

    maintenance_task.cancel()
    with suppress(asyncio.CancelledError):
        await maintenance_task
    if _nats_client is not None:
        await _nats_client.close()
    await dispose_engine()


app = FastAPI(
    title=settings.SERVICE_NAME,
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/api/docs" if settings.is_dev else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.is_dev else None,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
)

register_exception_handlers(app)
app.include_router(public_router)
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(card_messages_router)
app.include_router(categories_router)
app.include_router(templates_router)
app.include_router(imports_router)
app.include_router(analytics_router)
app.include_router(admins_router)
app.include_router(label_presets_router)
app.include_router(media_router)

setup_metrics(app)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> ORJSONResponse:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return ORJSONResponse({"status": "db_unavailable"}, status_code=503)
    return ORJSONResponse({"status": "ok"})
