import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import orjson
from nats.aio.msg import Msg
from nats.js.api import AckPolicy, DeliverPolicy, ReplayPolicy
from nats.js.api import ConsumerConfig as JSConsumerConfig
from pydantic import BaseModel, ValidationError

from std_cards.core.nats.client import NatsClient

logger = logging.getLogger(__name__)


@dataclass
class ConsumerConfig:
    """Декларативная конфигурация pull-консьюмера.

    Поля повторяют JS ConsumerConfig для прозрачности: имя, поток, фильтры,
    политики ack/replay. Фабрика `build_pull_consumer` создаёт consumer
    с этой конфигурацией; реальная подписка — на `consumer.start(nats_client, ...)`.
    """

    consumer_name: str
    jetstream_name: str
    filter_subjects: list[str]
    fetch_size: int = 5
    ack_wait_seconds: float = 30.0
    max_ack_pending: int = 100
    max_deliver: int = 5
    deliver_policy: DeliverPolicy = DeliverPolicy.ALL
    ack_policy: AckPolicy = AckPolicy.EXPLICIT
    replay_policy: ReplayPolicy = ReplayPolicy.INSTANT
    poll_timeout_seconds: float = 5.0
    handlers: dict[str, "Handler"] = field(default_factory=dict)


@dataclass
class NatsMessage[T: BaseModel]:
    data: T
    raw: Msg
    headers: dict[str, str]
    message_type: str

    async def ack(self) -> None:
        await self.raw.ack()

    async def nak(self, delay: float | None = None) -> None:
        await self.raw.nak(delay=delay)

    async def term(self) -> None:
        await self.raw.term()


@dataclass
class Handler:
    name: str
    callback: Callable[[NatsMessage[Any]], Awaitable[None]]
    data_model_in: type[BaseModel]
    timeout: float = 300.0


class PullConsumer:
    """Pull-консьюмер с роутингом по `message_type` header.

    Один consumer слушает несколько subjects, каждый message_type ассоциирован
    с handler-функцией. Несоответствие — ack + warn (чтобы не зацикливаться).
    """

    def __init__(self, config: ConsumerConfig) -> None:
        self.config = config
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._client: NatsClient | None = None

    def consume[T: BaseModel](
        self,
        message_type: str,
        data_model_in: type[T],
        timeout: float = 300.0,
    ) -> Callable[
        [Callable[[NatsMessage[T]], Awaitable[None]]], Callable[[NatsMessage[T]], Awaitable[None]]
    ]:
        """Декоратор регистрации handler для конкретного `message_type`."""

        def decorator(
            fn: Callable[[NatsMessage[T]], Awaitable[None]],
        ) -> Callable[[NatsMessage[T]], Awaitable[None]]:
            self.config.handlers[message_type] = Handler(
                name=message_type,
                callback=fn,  # type: ignore[arg-type]
                data_model_in=data_model_in,
                timeout=timeout,
            )
            return fn

        return decorator

    async def start(self, client: NatsClient, service_name: str, prefix: str) -> None:
        self._client = client
        durable = f"{prefix}-{self.config.consumer_name}"

        cfg = JSConsumerConfig(
            durable_name=durable,
            filter_subjects=self.config.filter_subjects,
            ack_policy=self.config.ack_policy,
            ack_wait=self.config.ack_wait_seconds,
            max_ack_pending=self.config.max_ack_pending,
            max_deliver=self.config.max_deliver,
            deliver_policy=self.config.deliver_policy,
            replay_policy=self.config.replay_policy,
        )
        try:
            await client.js.add_consumer(
                stream=self.config.jetstream_name,
                config=cfg,
            )
        except Exception as exc:
            logger.info("Consumer ensure (already exists or update): %s", exc)
        sub = await client.js.pull_subscribe_bind(
            durable=durable,
            stream=self.config.jetstream_name,
        )
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(sub), name=f"consumer:{durable}")
        logger.info(
            "Consumer started: stream=%s durable=%s subjects=%s",
            self.config.jetstream_name,
            durable,
            self.config.filter_subjects,
        )

    async def _run(self, sub: Any) -> None:
        backoff = 1.0
        while not self._stop_event.is_set():
            try:
                msgs = await sub.fetch(
                    self.config.fetch_size, timeout=self.config.poll_timeout_seconds
                )
                backoff = 1.0
            except TimeoutError:
                continue
            except Exception:
                logger.exception("Consumer fetch error: %s", self.config.consumer_name)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            for msg in msgs:
                await self._process_message(msg)

    async def _process_message(self, msg: Msg) -> None:
        headers = dict(msg.headers or {})
        message_type = headers.get("message_type")
        if not message_type:
            try:
                body = orjson.loads(msg.data)
                message_type = body.get("message_type")
            except Exception:
                message_type = None

        if not message_type:
            logger.warning("No message_type in headers/payload, terminating msg")
            await msg.term()
            return

        handler = self.config.handlers.get(message_type)
        if handler is None:
            logger.warning(
                "No handler for message_type=%s consumer=%s, ack",
                message_type,
                self.config.consumer_name,
            )
            await msg.ack()
            return

        try:
            body = orjson.loads(msg.data)
            payload = body.get("payload", body)
            data = handler.data_model_in.model_validate(payload)
        except (ValidationError, ValueError) as exc:
            logger.exception("Failed to parse message %s: %s", message_type, exc)
            await msg.term()
            return

        wrapped = NatsMessage(data=data, raw=msg, headers=headers, message_type=message_type)
        try:
            await asyncio.wait_for(handler.callback(wrapped), timeout=handler.timeout)
            await msg.ack()
        except TimeoutError:
            logger.exception("Handler timeout: %s", message_type)
            await msg.nak(delay=5.0)
        except Exception:
            logger.exception("Handler error: %s", message_type)
            await msg.nak(delay=5.0)

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except TimeoutError:
                self._task.cancel()
            except Exception:
                logger.exception("Error stopping consumer %s", self.config.consumer_name)
            self._task = None
        logger.info("Consumer stopped: %s", self.config.consumer_name)


def build_pull_consumer(config: ConsumerConfig) -> PullConsumer:
    return PullConsumer(config)
