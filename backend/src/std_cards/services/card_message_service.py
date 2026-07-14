import io
import logging
from uuid import UUID, uuid4

from PIL import Image, ImageOps

from std_cards.config import settings
from std_cards.core.exceptions import NotFoundError, ValidationFailedError
from std_cards.infrastructure.minio import MinioClient
from std_cards.infrastructure.repositories.card_message_repo import CardMessageRepository
from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.models.card_message import CardMessageCreate, CardMessageDB

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1600


class CardMessageService:
    def __init__(
        self,
        message_repo: CardMessageRepository,
        card_repo: CardRepository,
        minio: MinioClient,
    ):
        self.messages = message_repo
        self.cards = card_repo
        self.minio = minio

    async def upload_image(self, card_id: UUID, raw: bytes, content_type: str) -> str:
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise ValidationFailedError(message=f"Unsupported image type: {content_type}")
        if len(raw) > MAX_IMAGE_BYTES:
            raise ValidationFailedError(message="Image exceeds 5MB limit")
        try:
            img = Image.open(io.BytesIO(raw))
            img = ImageOps.exif_transpose(img)
            img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
            if img.mode != "RGB":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=85)
            processed = buf.getvalue()
        except ValidationFailedError:
            raise
        except Exception as exc:
            raise ValidationFailedError(message=f"Invalid image: {exc}") from exc

        card = await self.cards.get_by_id(card_id)
        if card is None:
            raise NotFoundError()

        key = f"card-messages/{card_id}/{uuid4().hex}.webp"
        await self.minio.upload(
            settings.MINIO.BUCKET_CARDS, key, processed, content_type="image/webp"
        )
        return key

    async def create_message(
        self,
        card_id: UUID,
        body: CardMessageCreate,
        actor_id: UUID,
    ) -> CardMessageDB:
        card = await self.cards.get_by_id(card_id)
        if card is None:
            raise NotFoundError()

        text_clean = body.text.strip()
        if not text_clean and not body.image_key:
            raise ValidationFailedError(
                message="Сообщение должно содержать текст или изображение",
            )

        return await self.messages.create(
            card_id=card_id,
            text=text_clean,
            image_key=body.image_key,
            created_by=actor_id,
        )

    async def list_for_card(self, card_id: UUID) -> list[CardMessageDB]:
        card = await self.cards.get_by_id(card_id)
        if card is None:
            raise NotFoundError()
        return await self.messages.list_active_for_card(card_id)

    async def delete_message(self, card_id: UUID, message_id: UUID) -> None:
        card = await self.cards.get_by_id(card_id)
        if card is None:
            raise NotFoundError()
        deleted = await self.messages.soft_delete(message_id, card_id)
        if not deleted:
            raise NotFoundError()
