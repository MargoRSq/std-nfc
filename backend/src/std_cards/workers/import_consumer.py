from uuid import UUID

from pydantic import BaseModel

from std_cards.core.nats.consumer import ConsumerConfig, NatsMessage, build_pull_consumer

consumer = build_pull_consumer(
    ConsumerConfig(
        consumer_name="import-worker",
        jetstream_name="CARDS_IMPORT",
        filter_subjects=["cards.import.process"],
        fetch_size=1,
        ack_wait_seconds=600.0,
        max_ack_pending=1,
        max_deliver=3,
    )
)


class ImportRequestEvent(BaseModel):
    job_id: UUID


@consumer.consume("import_request", data_model_in=ImportRequestEvent, timeout=600.0)
async def _handle_import_request(message: NatsMessage[ImportRequestEvent]) -> None:
    from std_cards.db.session import get_session_maker
    from std_cards.infrastructure.minio import get_minio
    from std_cards.infrastructure.repositories import (
        CardRepository,
        ImportJobRepository,
        TemplateRepository,
    )
    from std_cards.services.import_service import ImportService

    sm = get_session_maker()
    service = ImportService(
        import_repo=ImportJobRepository(sm),
        card_repo=CardRepository(sm),
        template_repo=TemplateRepository(sm),
        minio=get_minio(),
        nats_publisher=None,
    )
    await service.process_job(message.data.job_id)
