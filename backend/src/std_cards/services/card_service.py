import io
import re
from uuid import UUID

import sqlalchemy as sa
from openpyxl import Workbook

from std_cards.config import settings
from std_cards.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationFailedError,
)
from std_cards.core.slug import is_valid_slug
from std_cards.infrastructure.repositories.admin_card_groups_repo import AdminCardGroupRepository
from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.category_repo import CategoryRepository
from std_cards.infrastructure.repositories.db_models import admin_card_groups, cards
from std_cards.infrastructure.repositories.template_repo import TemplateRepository
from std_cards.logo_presets import default_logo_key
from std_cards.models.auth import UserDB, UserRole
from std_cards.models.card import (
    BackgroundGradient,
    CardCreate,
    CardDB,
    CardsList,
    CardsListFilter,
    CardUpdate,
)
from std_cards.models.template import TemplateDB
from std_cards.services.slug_service import SlugService

_HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _is_hex6(v: object) -> bool:
    return isinstance(v, str) and bool(_HEX6.match(v))


def compute_template_overrides(
    *,
    current_bg_kind: str,
    current_bg_color: str | None,
    current_bg_gradient: dict | BackgroundGradient | None,
    current_photo_shape: str,
    current_chairman: str | None,
    current_region: str | None,
    template: TemplateDB,
    current_logo_key: str | None = None,
    current_logo_shape: str | None = None,
    current_avatar_color: str | None = None,
    current_avatar_gradient: dict | BackgroundGradient | None = None,
    current_contacts: list | None = None,
    current_label_set: list | None = None,
) -> dict:
    styles = template.default_styles or {}
    fields = template.default_fields or {}
    schema = template.custom_field_schema or []
    update: dict = {}

    if current_bg_kind == "solid" and current_bg_color is None and current_bg_gradient is None:
        tpl_bg_kind = styles.get("bg_kind")
        if tpl_bg_kind == "gradient":
            grad = styles.get("bg_gradient") or {}
            from_c = grad.get("from") or grad.get("start")
            to_c = grad.get("to") or grad.get("end")
            if from_c and to_c:
                update["bg_kind"] = "gradient"
                update["bg_gradient"] = BackgroundGradient(
                    **{"from": from_c, "to": to_c, "angle": grad.get("angle", 135)}
                )
        elif tpl_bg_kind == "solid":
            bg_color = styles.get("bg_color")
            if _is_hex6(bg_color):
                update["bg_kind"] = "solid"
                update["bg_color"] = bg_color

    if current_photo_shape == "square" and styles.get("photo_shape") in ("square", "circle"):
        update["photo_shape"] = styles["photo_shape"]

    if current_logo_key is None and styles.get("logo_key"):
        update["logo_key"] = styles["logo_key"]
    if current_logo_shape is None and styles.get("logo_shape") in ("square", "circle", "rectangle"):
        update["logo_shape"] = styles["logo_shape"]

    if current_avatar_color is None and current_avatar_gradient is None:
        if styles.get("avatar_gradient"):
            grad = styles["avatar_gradient"]
            from_c = grad.get("from") or grad.get("start")
            to_c = grad.get("to") or grad.get("end")
            if from_c and to_c:
                update["avatar_gradient"] = BackgroundGradient(
                    **{"from": from_c, "to": to_c, "angle": grad.get("angle", 135)}
                )
        elif _is_hex6(styles.get("avatar_color")):
            update["avatar_color"] = styles["avatar_color"]

    if not current_chairman and fields.get("chairman"):
        update["chairman"] = fields["chairman"]
    if not current_region and fields.get("region"):
        update["region"] = fields["region"]

    if not current_contacts and isinstance(fields.get("contacts"), list):
        update["contacts"] = fields["contacts"]

    if not current_label_set and isinstance(schema, list) and schema:
        update["label_set"] = schema

    return update


async def build_acl_filter(user: UserDB, group_repo: AdminCardGroupRepository):
    if user.role == UserRole.SUPER_ADMIN:
        return None
    cats = await group_repo.categories_for_user(user.id)
    if not cats:
        return cards.c.assigned_admin_id == user.id
    return sa.or_(
        cards.c.assigned_admin_id == user.id,
        cards.c.category_id.in_(
            sa.select(admin_card_groups.c.category_id).where(admin_card_groups.c.user_id == user.id)
        ),
    )


class CardService:
    def __init__(
        self,
        card_repo: CardRepository,
        slug_service: SlugService,
        category_repo: CategoryRepository,
        group_repo: AdminCardGroupRepository | None = None,
        template_repo: TemplateRepository | None = None,
    ) -> None:
        self.cards = card_repo
        self.slug = slug_service
        self.categories = category_repo
        self.groups = group_repo
        self.templates = template_repo

    async def _acl(self, user: UserDB):
        if self.groups is None:
            return None
        return await build_acl_filter(user, self.groups)

    async def create(self, data: CardCreate, created_by: UUID) -> CardDB:
        if await self.cards.membership_no_exists(data.membership_no):
            raise ConflictError(
                message=f"Удостоверение с номером «{data.membership_no.strip()}» уже существует",
                details={"field": "membership_no"},
            )
        if data.category_id is None:
            data = await self._resolve_default_category(data)
        cat = await self.categories.get_by_id(data.category_id)
        if cat is None:
            raise ValidationFailedError(message=f"Unknown category_id {data.category_id}")
        if data.template_id is not None and self.templates is not None:
            data = await self._apply_template_defaults(data)
        if data.logo_key is None:
            data = data.model_copy(update={"logo_key": default_logo_key()})
        slug = await self.slug.ensure_unique(data.public_slug)
        return await self.cards.create(data, slug=slug, created_by=created_by)

    async def _resolve_default_category(self, data: CardCreate) -> CardCreate:
        if data.template_id is not None and self.templates is not None:
            tpl = await self.templates.get_by_id(data.template_id)
            if tpl is not None:
                return data.model_copy(update={"category_id": tpl.category_id})
        if self.templates is not None:
            default_tpl = await self.templates.get_default()
            if default_tpl is not None:
                return data.model_copy(
                    update={"category_id": default_tpl.category_id, "template_id": default_tpl.id},
                )
        cats = await self.categories.list_all()
        # Без шаблона — «Стандартная», а не первая попавшаяся: иначе член без
        # выбранной категории молча получал уровень (Платиновые/Бронзовые).
        standard = next((c for c in cats if c.code == "standard"), None)
        if standard is not None:
            return data.model_copy(update={"category_id": standard.id})
        if cats:
            return data.model_copy(update={"category_id": cats[0].id})
        raise ValidationFailedError(message="No categories or default template configured")

    async def _apply_template_defaults(self, data: CardCreate) -> CardCreate:
        if data.template_id is None or self.templates is None:
            return data
        tpl = await self.templates.get_by_id(data.template_id)
        if tpl is None:
            return data
        update = compute_template_overrides(
            current_bg_kind=data.bg_kind,
            current_bg_color=data.bg_color,
            current_bg_gradient=data.bg_gradient,
            current_photo_shape=data.photo_shape,
            current_chairman=data.chairman,
            current_region=data.region,
            current_logo_key=data.logo_key,
            current_logo_shape=data.logo_shape,
            current_avatar_color=data.avatar_color,
            current_avatar_gradient=data.avatar_gradient,
            current_contacts=data.contacts,
            current_label_set=data.label_set,
            template=tpl,
        )
        if not update:
            return data
        return data.model_copy(update=update)

    async def apply_template(
        self, id: UUID, template_id: UUID, current_user: UserDB | None = None
    ) -> CardDB:
        acl_filter = await self._acl(current_user) if current_user else None
        card = await self.cards.get_by_id(id, acl_filter=acl_filter)
        if card is None:
            raise NotFoundError()
        if self.templates is None:
            raise ValidationFailedError(message="Templates not configured")
        tpl = await self.templates.get_by_id(template_id)
        if tpl is None:
            raise NotFoundError()
        overrides = compute_template_overrides(
            current_bg_kind=card.bg_kind,
            current_bg_color=card.bg_color,
            current_bg_gradient=card.bg_gradient,
            current_photo_shape=card.photo_shape,
            current_chairman=card.chairman,
            current_region=card.region,
            current_logo_key=card.logo_key,
            current_logo_shape=card.logo_shape,
            current_avatar_color=card.avatar_color,
            current_avatar_gradient=card.avatar_gradient,
            current_contacts=card.contacts,
            current_label_set=card.label_set,
            template=tpl,
        )
        if tpl.category_id is not None:
            overrides["category_id"] = tpl.category_id
        update_payload = CardUpdate(template_id=template_id, **overrides)
        updated = await self.cards.update(id, update_payload)
        if updated is None:
            raise NotFoundError()
        return updated

    async def get(self, id: UUID, current_user: UserDB | None = None) -> CardDB:
        acl_filter = await self._acl(current_user) if current_user else None
        card = await self.cards.get_by_id(id, acl_filter=acl_filter)
        if card is None:
            raise NotFoundError()
        return card

    async def list(self, filter: CardsListFilter, current_user: UserDB | None = None) -> CardsList:
        acl_filter = await self._acl(current_user) if current_user else None
        items, total = await self.cards.list(filter, acl_filter=acl_filter)
        return CardsList(items=items, total=total, page=filter.page, page_size=filter.page_size)

    async def update(
        self, id: UUID, data: CardUpdate, current_user: UserDB | None = None
    ) -> CardDB:
        if current_user:
            acl_filter = await self._acl(current_user)
            existing = await self.cards.get_by_id(id, acl_filter=acl_filter)
            if existing is None:
                raise NotFoundError()
            if current_user.role != UserRole.SUPER_ADMIN:
                if (
                    data.assigned_admin_id is not None
                    and data.assigned_admin_id != existing.assigned_admin_id
                ):
                    raise ForbiddenError(message="Недостаточно прав для переназначения карточки")
                if data.category_id is not None and data.category_id != existing.category_id:
                    allowed = (
                        set(await self.groups.categories_for_user(current_user.id))
                        if self.groups
                        else set()
                    )
                    if data.category_id not in allowed:
                        raise ForbiddenError(message="Недостаточно прав для смены категории")

        if data.membership_no is not None and await self.cards.membership_no_exists(
            data.membership_no, exclude_id=id
        ):
            raise ConflictError(
                message=f"Удостоверение с номером «{data.membership_no.strip()}» уже существует",
                details={"field": "membership_no"},
            )

        updated = await self.cards.update(id, data)
        if updated is None:
            raise NotFoundError()
        return updated

    async def delete(self, id: UUID, current_user: UserDB | None = None) -> None:
        acl_filter = await self._acl(current_user) if current_user else None
        ok = await self.cards.soft_delete(id, acl_filter=acl_filter)
        if not ok:
            raise NotFoundError()

    async def regenerate_slug(self, id: UUID, custom: str | None = None) -> str:
        new_slug = await self.slug.ensure_unique(custom)
        await self.cards.update_slug(id, new_slug)
        return new_slug

    async def check_slug(self, slug: str, exclude_id: UUID | None = None) -> bool:
        if not is_valid_slug(slug):
            return False
        existing = await self.cards.get_by_slug(slug, include_deleted=True)
        if existing is None:
            return True
        return existing.id == exclude_id

    async def export_all_xlsx(self) -> tuple[bytes, int]:
        """Build full xlsx export of all (non-deleted) cards.

        Returns (file_bytes, row_count). Uses openpyxl write-only workbook to
        keep memory usage low for large datasets (50K rows ~ tens of MB peak).
        """
        cat_list = await self.categories.list_all()
        category_names = {c.id: c.name_ru for c in cat_list}

        base_url = (settings.PUBLIC_CARD_BASE_URL or settings.FRONTEND_URL or "").rstrip("/")
        if base_url.startswith("http://localhost") or base_url == "":
            base_url = (
                settings.PUBLIC_CARD_BASE_URL.rstrip("/")
                if settings.PUBLIC_CARD_BASE_URL
                else base_url
            )

        wb = Workbook(write_only=True)
        ws = wb.create_sheet("Cards")
        headers = [
            "Public URL",
            "Slug",
            "Фамилия",
            "Имя",
            "Отчество",
            "Номер удостоверения",
            "Категория",
            "Регион",
            "Дата рождения",
            "Дата выдачи",
            "Дата вступления",
            "Председатель",
            "Создано",
            "Активна",
        ]
        ws.append(headers)

        row_count = 0
        async for r in self.cards.iter_all_for_export(batch_size=500):
            slug = r["public_slug"]
            public_url = f"{base_url}/c/{slug}" if base_url else f"/c/{slug}"
            ws.append(
                [
                    public_url,
                    slug,
                    r["last_name"] or "",
                    r["first_name"] or "",
                    r["middle_name"] or "",
                    r["membership_no"] or "",
                    category_names.get(r["category_id"], "")
                    if r["category_id"] is not None
                    else "",
                    r["region"] or "",
                    r["birth_date"].isoformat() if r["birth_date"] else "",
                    r["card_issue_date"].isoformat() if r["card_issue_date"] else "",
                    r["join_date"].isoformat() if r["join_date"] else "",
                    r["chairman"] or "",
                    r["created_at"].isoformat() if r["created_at"] else "",
                    "да" if r["is_active"] else "нет",
                ]
            )
            row_count += 1

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), row_count
