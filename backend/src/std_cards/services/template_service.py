from typing import Literal
from uuid import UUID

from std_cards.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.category_repo import CategoryRepository
from std_cards.infrastructure.repositories.template_repo import TemplateRepository
from std_cards.models.template import TemplateCreate, TemplateDB, TemplateUpdate

DeleteCascade = Literal["template_only", "with_cards"]


class TemplateService:
    def __init__(
        self,
        repo: TemplateRepository,
        card_repo: CardRepository,
        category_repo: CategoryRepository,
    ) -> None:
        self.templates = repo
        self.cards = card_repo
        self.categories = category_repo

    async def list_all(self) -> list[TemplateDB]:
        return await self.templates.list_all()

    async def get(self, id: UUID) -> TemplateDB:
        tpl = await self.templates.get_by_id(id)
        if tpl is None:
            raise NotFoundError()
        return tpl

    async def create(self, data: TemplateCreate, created_by: UUID) -> TemplateDB:
        cat = await self.categories.get_by_id(data.category_id)
        if cat is None:
            raise ValidationFailedError(message=f"Unknown category_id {data.category_id}")
        try:
            return await self.templates.create(data, created_by=created_by)
        except Exception as exc:
            if "uq_templates_name_category_id" in str(exc):
                raise ConflictError(
                    message=f"Template '{data.name}' already exists in this category"
                ) from exc
            raise

    async def update(self, id: UUID, data: TemplateUpdate) -> TemplateDB:
        if data.category_id is not None:
            cat = await self.categories.get_by_id(data.category_id)
            if cat is None:
                raise ValidationFailedError(message=f"Unknown category_id {data.category_id}")
        try:
            updated = await self.templates.update(id, data)
        except Exception as exc:
            if "uq_templates_name_category_id" in str(exc):
                raise ConflictError(
                    message="Template with this name already exists in the category"
                ) from exc
            raise
        if updated is None:
            raise NotFoundError()
        return updated

    async def delete(self, id: UUID, cascade: DeleteCascade = "template_only") -> dict:
        tpl = await self.templates.get_by_id(id)
        if tpl is None:
            raise NotFoundError()
        if tpl.is_default:
            raise ConflictError(message="Нельзя удалить шаблон по умолчанию")

        if cascade == "with_cards":
            cards_affected = await self.cards.soft_delete_by_template(id)
            ok = await self.templates.delete(id)
            if not ok:
                raise NotFoundError()
            return {"cards_deleted": cards_affected, "cards_reassigned": 0}

        default = await self.templates.get_default()
        cards_affected = 0
        if default is not None:
            cards_affected = await self.cards.reassign_template(id, default.id)
        ok = await self.templates.delete(id)
        if not ok:
            raise NotFoundError()
        return {"cards_deleted": 0, "cards_reassigned": cards_affected}

    async def duplicate(self, id: UUID, new_name: str) -> TemplateDB:
        duplicated = await self.templates.duplicate(id, new_name)
        if duplicated is None:
            raise NotFoundError()
        return duplicated

    async def from_card(self, card_id: UUID, name: str, created_by: UUID) -> TemplateDB:
        card = await self.cards.get_by_id(card_id)
        if card is None:
            raise NotFoundError()
        return await self.templates.create(
            TemplateCreate(
                name=name,
                category_id=card.category_id,
                default_styles={
                    "bg_kind": card.bg_kind,
                    "bg_color": card.bg_color,
                    "bg_gradient": card.bg_gradient,
                    "photo_shape": card.photo_shape,
                },
                custom_field_schema=[
                    {"key": k, **v} for k, v in card.custom_fields.items() if isinstance(v, dict)
                ],
            ),
            created_by=created_by,
        )

    async def apply(self, template_id: UUID, card_id: UUID) -> None:
        tpl = await self.templates.get_by_id(template_id)
        if tpl is None:
            raise NotFoundError(message="Template not found")
        card = await self.cards.get_by_id(card_id)
        if card is None:
            raise NotFoundError(message="Card not found")
