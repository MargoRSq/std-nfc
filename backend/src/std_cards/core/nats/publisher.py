import logging
from typing import Any

import orjson
from pydantic import BaseModel

from std_cards.core.nats.client import NatsClient

logger = logging.getLogger(__name__)


def _serialize(payload: Any) -> bytes:
    if isinstance(payload, BaseModel):
        return payload.model_dump_json().encode("utf-8")
    return orjson.dumps(payload)


class NatsPublisher:
    """Публикация сообщений в NATS (core или JetStream subjects).

    Domain-specific publishers подкласируют `NatsPublisherApi` и используют
    этот класс через композицию.
    """

    def __init__(self, client: NatsClient) -> None:
        self.client = client

    async def publish(
        self,
        subject: str,
        message_type: str,
        payload: Any,
        headers: dict[str, str] | None = None,
        msg_id: str | None = None,
    ) -> None:
        body = _serialize({"message_type": message_type, "payload": payload})
        merged_headers: dict[str, str] = {"message_type": message_type}
        if headers:
            merged_headers.update(headers)
        if msg_id:
            merged_headers["Nats-Msg-Id"] = msg_id

        await self.client.js.publish(subject, body, headers=merged_headers)
        logger.debug("Published %s → %s", message_type, subject)

    async def publish_core(
        self,
        subject: str,
        message_type: str,
        payload: Any,
    ) -> None:
        body = _serialize({"message_type": message_type, "payload": payload})
        await self.client.nc.publish(subject, body)
        logger.debug("Published(core) %s → %s", message_type, subject)
