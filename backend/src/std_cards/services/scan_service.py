import logging
from datetime import UTC, datetime
from uuid import UUID

from std_cards.core.nats.publisher import NatsPublisher

logger = logging.getLogger(__name__)


class ScanService:
    def __init__(self, nats_publisher: NatsPublisher | None = None) -> None:
        self.nats = nats_publisher

    async def publish_scan(
        self,
        card_id: UUID,
        ip: str | None,
        user_agent: str | None,
        referer: str | None,
    ) -> None:
        if self.nats is None:
            logger.debug("NATS not available, skipping scan publish")
            return
        try:
            await self.nats.publish(
                subject="cards.scan.recorded",
                message_type="scan_recorded",
                payload={
                    "card_id": str(card_id),
                    "ts": datetime.now(UTC).isoformat(),
                    "ip": ip,
                    "user_agent": user_agent,
                    "referer": referer,
                },
            )
        except Exception:
            logger.exception("Failed to publish scan event for card %s", card_id)
