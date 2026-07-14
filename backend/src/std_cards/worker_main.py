import asyncio
import contextlib
import logging
import signal

from std_cards.config import settings
from std_cards.core.nats.client import NatsClient
from std_cards.db.partitions import ensure_upcoming_partitions
from std_cards.db.session import dispose_engine, get_session_maker
from std_cards.infrastructure.handlers import run_all_consumers, stop_all_consumers
from std_cards.infrastructure.repositories import (
    LoginChallengeRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
)

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

MAINTENANCE_INTERVAL_SECONDS = 3600


async def _run_db_maintenance() -> None:
    """Pre-create upcoming scan_events partitions and purge expired auth rows.
    Runs in the worker (single deployment) so it isn't duplicated per API replica."""
    sm = get_session_maker()
    async with sm.session() as conn:
        await ensure_upcoming_partitions(conn)
    await RefreshTokenRepository(sm).cleanup_expired()
    await LoginChallengeRepository(sm).cleanup_expired()
    await PasswordResetRepository(sm).cleanup_expired()


async def _db_maintenance_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await _run_db_maintenance()
        except Exception:
            logger.exception("db maintenance failed")
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=MAINTENANCE_INTERVAL_SECONDS)


async def main() -> None:
    nats_client = NatsClient(settings.SERVICE_NAME)
    await nats_client.connect(settings.NATS.URL)

    await nats_client.ensure_stream(
        "CARDS_IMPORT",
        subjects=["cards.import.process", "cards.import.progress.>"],
    )
    await nats_client.ensure_stream(
        "CARDS_SCAN",
        subjects=["cards.scan.recorded", "cards.feedback.received"],
    )

    if settings.NATS.CONSUMER_START:
        await run_all_consumers(
            nats_client=nats_client,
            service_name=settings.SERVICE_NAME,
            prefix=settings.CONSUMER_PREFIX,
        )

    logger.info("Worker started, waiting for messages…")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    maintenance_task = asyncio.create_task(_db_maintenance_loop(stop), name="db-maintenance")
    try:
        await stop.wait()
    finally:
        logger.info("Worker shutting down")
        maintenance_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await maintenance_task
        try:
            if settings.NATS.CONSUMER_START:
                await stop_all_consumers()
        finally:
            await nats_client.close()
            await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
