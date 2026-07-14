import logging

import nats
from nats.aio.client import Client as NATSClient
from nats.js import JetStreamContext
from nats.js.api import RetentionPolicy, StorageType, StreamConfig

logger = logging.getLogger(__name__)


class NatsClient:
    """Тонкая обёртка вокруг nats-py с lifecycle-методами и helper для streams.

    Используется один экземпляр на процесс. Создаётся в lifespan main.py
    и пробрасывается в Publisher/Consumer.
    """

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self._nc: NATSClient | None = None
        self._js: JetStreamContext | None = None

    @property
    def nc(self) -> NATSClient:
        if self._nc is None:
            raise RuntimeError("NATS client is not connected; call connect() first")
        return self._nc

    @property
    def js(self) -> JetStreamContext:
        if self._js is None:
            raise RuntimeError("JetStream context is not initialised")
        return self._js

    async def connect(self, url: str) -> None:
        logger.info("Connecting to NATS %s", url)
        self._nc = await nats.connect(url, name=self.service_name)
        self._js = self._nc.jetstream()

    async def close(self) -> None:
        if self._nc is None:
            return
        try:
            await self._nc.drain()
        except Exception:
            logger.exception("Error draining NATS connection")
        finally:
            self._nc = None
            self._js = None

    async def ensure_stream(
        self,
        name: str,
        subjects: list[str],
        retention: RetentionPolicy = RetentionPolicy.WORK_QUEUE,
        storage: StorageType = StorageType.FILE,
        max_age_seconds: int = 0,
        replicas: int = 1,
    ) -> None:
        """Идемпотентно создаёт/обновляет stream.

        Вызывается в lifespan на старте сервиса. Std-cards streams:
          - CARDS_IMPORT (subjects: cards.import.process, cards.import.progress.>)
          - CARDS_SCAN   (subject: cards.scan.recorded)
        """
        cfg = StreamConfig(
            name=name,
            subjects=subjects,
            retention=retention,
            storage=storage,
            num_replicas=replicas,
            max_age=max_age_seconds * 1_000_000_000 if max_age_seconds else 0,
        )
        try:
            await self.js.add_stream(cfg)
            logger.info("NATS stream ensured: %s subjects=%s", name, subjects)
        except Exception:
            try:
                await self.js.update_stream(cfg)
                logger.info("NATS stream updated: %s", name)
            except Exception:
                logger.exception("Failed to ensure NATS stream %s", name)
                raise
