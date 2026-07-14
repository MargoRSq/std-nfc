import io
import logging
import re
from uuid import uuid4

from PIL import Image, ImageOps

from std_cards.config import settings
from std_cards.core.exceptions import NotFoundError, ValidationFailedError
from std_cards.infrastructure.minio import MinioClient
from std_cards.infrastructure.repositories.card_repo import CardRepository

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_DIMENSION = 1024

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# Public media is served unauthenticated (embedded in public cards), so the key
# must be a strict allow-list of real card-asset shapes — never an arbitrary
# bucket path. Blocks traversal and reads of non-asset objects.
_MEDIA_KEY_RE = re.compile(
    rf"^cards/{_UUID}/(?:photo|logo)-[0-9a-f]{{8}}\.webp$"
    rf"|^card-messages/{_UUID}/[0-9a-f]{{32}}\.webp$"
)


class MediaService:
    def __init__(self, minio: MinioClient, card_repo: CardRepository):
        self.minio = minio
        self.cards = card_repo

    def _process_image(self, raw: bytes, content_type: str) -> bytes:
        if content_type not in ALLOWED_TYPES:
            raise ValidationFailedError(message=f"Unsupported image type: {content_type}")
        try:
            img = Image.open(io.BytesIO(raw))
            img = ImageOps.exif_transpose(img)
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
            has_alpha = img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            )
            if has_alpha:
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
            elif img.mode != "RGB":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=85)
            return buf.getvalue()
        except ValidationFailedError:
            raise
        except Exception as exc:
            raise ValidationFailedError(message=f"Invalid image: {exc}") from exc

    async def upload_card_photo(self, card_id, raw: bytes, content_type: str) -> str:
        card = await self.cards.get_by_id(card_id)
        if card is None:
            raise NotFoundError()
        processed = self._process_image(raw, content_type)
        key = f"cards/{card_id}/photo-{uuid4().hex[:8]}.webp"
        await self.minio.upload(
            settings.MINIO.BUCKET_CARDS, key, processed, content_type="image/webp"
        )
        await self.cards.set_photo_key(card_id, key)
        return key

    async def upload_card_logo(self, card_id, raw: bytes, content_type: str) -> str:
        card = await self.cards.get_by_id(card_id)
        if card is None:
            raise NotFoundError()
        processed = self._process_image(raw, content_type)
        key = f"cards/{card_id}/logo-{uuid4().hex[:8]}.webp"
        await self.minio.upload(
            settings.MINIO.BUCKET_CARDS, key, processed, content_type="image/webp"
        )
        await self.cards.set_logo_key(card_id, key)
        return key

    async def stream_media(self, key: str) -> tuple[bytes, str]:
        if not _MEDIA_KEY_RE.match(key):
            raise NotFoundError()
        try:
            data = await self.minio.download(settings.MINIO.BUCKET_CARDS, key)
            return data, "image/webp"
        except Exception as exc:
            raise NotFoundError() from exc
