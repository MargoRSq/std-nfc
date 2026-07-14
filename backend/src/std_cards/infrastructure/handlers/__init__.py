"""NATS consumer registry.

Каждый consumer лежит в отдельном файле и собирается в `ALL_CONSUMERS`.
В lifespan вызываются `run_all_consumers` / `stop_all_consumers`.

Паттерн скопирован из tms-recommendations: декларативная конфигурация
+ единый registry для bulk start/stop, упрощает добавление новых типов событий.

Конкретные consumers добавляются:
- import_consumer — Phase 4
- scan_consumer   — Phase 5
- maintenance     — Phase 5 (партиции)
"""

import asyncio
from collections.abc import Sequence

from std_cards.core.nats.client import NatsClient
from std_cards.core.nats.consumer import PullConsumer
from std_cards.workers.import_consumer import consumer as import_consumer
from std_cards.workers.scan_consumer import consumer as scan_consumer

ALL_CONSUMERS: Sequence[PullConsumer] = (import_consumer, scan_consumer)


async def run_all_consumers(
    nats_client: NatsClient,
    service_name: str,
    prefix: str,
) -> None:
    for consumer in ALL_CONSUMERS:
        await consumer.start(nats_client, service_name, prefix)


async def stop_all_consumers() -> None:
    if not ALL_CONSUMERS:
        return
    await asyncio.gather(*[consumer.stop() for consumer in ALL_CONSUMERS], return_exceptions=True)
