from std_cards.core.exceptions import ConflictError, ValidationFailedError
from std_cards.core.slug import gen_slug, is_valid_slug
from std_cards.infrastructure.repositories.card_repo import CardRepository


class SlugService:
    def __init__(self, card_repo: CardRepository) -> None:
        self.cards = card_repo

    async def ensure_unique(self, slug: str | None = None, *, max_retries: int = 5) -> str:
        if slug is not None:
            if not is_valid_slug(slug):
                raise ValidationFailedError(message="Invalid slug format")
            if await self.cards.slug_exists(slug):
                raise ConflictError(message="URL уже занят")
            return slug
        for _ in range(max_retries):
            candidate = gen_slug(6)
            if not await self.cards.slug_exists(candidate):
                return candidate
        for _ in range(max_retries):
            candidate = gen_slug(7)
            if not await self.cards.slug_exists(candidate):
                return candidate
        raise RuntimeError("Failed to generate unique slug")
