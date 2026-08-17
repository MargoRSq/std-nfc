from datetime import date
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import cards
from std_cards.models.card import CardCreate, CardDB, CardListItem, CardsListFilter, CardUpdate

_SORT_MAP = {
    "created_at": cards.c.created_at.asc(),
    "-created_at": cards.c.created_at.desc(),
    "updated_at": cards.c.updated_at.asc(),
    "-updated_at": cards.c.updated_at.desc(),
    "last_name": sa.func.lower(cards.c.last_name).asc(),
    "-last_name": sa.func.lower(cards.c.last_name).desc(),
    "membership_no": cards.c.membership_no.asc(),
    "-membership_no": cards.c.membership_no.desc(),
    "category_id": cards.c.category_id.asc(),
    "-category_id": cards.c.category_id.desc(),
    "birth_date": cards.c.birth_date.asc().nulls_last(),
    "-birth_date": cards.c.birth_date.desc().nulls_last(),
    "region": sa.func.lower(cards.c.region).asc().nulls_last(),
    "-region": sa.func.lower(cards.c.region).desc().nulls_last(),
}

_DATE_FIELD_MAP = {
    "added": cards.c.created_at,
    "created": cards.c.created_at,
    "opened": cards.c.last_opened_at,
    "modified": cards.c.updated_at,
    "issued": cards.c.card_issue_date,
}

_LIST_COLS = [
    cards.c.id,
    cards.c.public_slug,
    cards.c.last_name,
    cards.c.first_name,
    cards.c.middle_name,
    cards.c.membership_no,
    cards.c.category_id,
    cards.c.region,
    cards.c.is_active,
    cards.c.photo_key,
    cards.c.birth_date,
    cards.c.bg_kind,
    cards.c.bg_color,
    cards.c.bg_gradient,
    cards.c.template_id,
    cards.c.created_at,
]


def _shift_years(d: date, years: int) -> date:
    """d минус `years` лет; 29 февраля в невисокосном году → 28 февраля."""
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return d.replace(year=d.year - years, day=28)


def normalize_gradient(value):
    """Приводит градиент к ключам `from`/`to` — их читают card.html и превью.

    `model_dump(mode="python")` разворачивает вложенный BackgroundGradient по
    именам полей (`from_color`/`to_color`), а не по алиасам, и в БД уезжал
    формат, которого рендер не понимает: карточка после «Назначить шаблон»
    рисовалась дефолтным градиентом вместо цветов шаблона. Легаси `start`/`end`
    из ранних версий приводим сюда же.
    """
    if not isinstance(value, dict):
        return value
    out = dict(value)
    for canonical, legacy in (("from", ("from_color", "start")), ("to", ("to_color", "end"))):
        if canonical in out:
            continue
        for key in legacy:
            if key in out:
                out[canonical] = out.pop(key)
                break
    for key in ("from_color", "to_color", "start", "end"):
        out.pop(key, None)
    return out


def build_card_filters(filter: CardsListFilter, acl_filter=None) -> list:
    """Условия WHERE, общие для списка карточек и выгрузки в Excel."""
    where = [cards.c.deleted_at.is_(None)]

    if filter.q:
        where.append(
            cards.c.full_name_search.contains(sa.func.immutable_unaccent(sa.func.lower(filter.q)))
        )
    if filter.category_id is not None:
        where.append(cards.c.category_id == filter.category_id)
    if filter.region is not None:
        where.append(cards.c.region == filter.region)
    date_col = _DATE_FIELD_MAP.get(filter.date_field or "issued", cards.c.card_issue_date)
    if filter.date_from is not None:
        where.append(date_col >= filter.date_from)
    if filter.date_to is not None:
        where.append(date_col <= filter.date_to)
    today = date.today()
    if filter.age_from is not None:
        where.append(cards.c.birth_date <= _shift_years(today, filter.age_from))
    if filter.age_to is not None:
        where.append(cards.c.birth_date > _shift_years(today, filter.age_to + 1))
    if filter.is_active is not None:
        where.append(cards.c.is_active == filter.is_active)
    if acl_filter is not None:
        where.append(acl_filter)
    return where


class CardRepository(BaseRepository):
    async def create(
        self,
        data: CardCreate,
        slug: str,
        created_by: UUID,
        conn: AsyncConnection | None = None,
    ) -> CardDB:
        values = data.model_dump(mode="python", exclude={"public_slug"})
        values["public_slug"] = slug
        values["created_by"] = created_by
        if values.get("label_set"):
            values["label_set"] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in values["label_set"]
            ]
        if values.get("contacts"):
            values["contacts"] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in values["contacts"]
            ]
        for key in ("bg_gradient", "avatar_gradient"):
            if values.get(key):
                values[key] = normalize_gradient(values[key])

        result = await self.ctx_wrap(
            sa.insert(cards).values(**values).returning(cards),
            conn,
        )
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create card")
        return CardDB.model_validate(row, from_attributes=True)

    async def get_by_id(
        self,
        id: UUID,
        *,
        include_deleted: bool = False,
        acl_filter=None,
        conn: AsyncConnection | None = None,
    ) -> CardDB | None:
        q = sa.select(cards).where(cards.c.id == id)
        if not include_deleted:
            q = q.where(cards.c.deleted_at.is_(None))
        if acl_filter is not None:
            q = q.where(acl_filter)
        result = await self.ctx_wrap(q, conn)
        row = result.fetchone()
        return CardDB.model_validate(row, from_attributes=True) if row else None

    async def get_by_slug(
        self,
        slug: str,
        *,
        include_deleted: bool = False,
        conn: AsyncConnection | None = None,
    ) -> CardDB | None:
        q = sa.select(cards).where(cards.c.public_slug == slug)
        if not include_deleted:
            q = q.where(cards.c.deleted_at.is_(None))
        result = await self.ctx_wrap(q, conn)
        row = result.fetchone()
        return CardDB.model_validate(row, from_attributes=True) if row else None

    async def distinct_regions(
        self,
        *,
        acl_filter=None,
        conn: AsyncConnection | None = None,
    ) -> list[tuple[str, int]]:
        where = [
            cards.c.deleted_at.is_(None),
            cards.c.region.isnot(None),
            cards.c.region != "",
        ]
        if acl_filter is not None:
            where.append(acl_filter)
        q = (
            sa.select(cards.c.region, sa.func.count())
            .where(sa.and_(*where))
            .group_by(cards.c.region)
            .order_by(sa.func.lower(cards.c.region))
        )
        result = await self.ctx_wrap(q, conn)
        return [(row[0], row[1]) for row in result.fetchall()]

    async def list(
        self,
        filter: CardsListFilter,
        *,
        acl_filter=None,
        conn: AsyncConnection | None = None,
    ) -> tuple[list[CardListItem], int]:
        base_where = build_card_filters(filter, acl_filter)

        count_q = sa.select(sa.func.count()).select_from(cards).where(sa.and_(*base_where))
        count_result = await self.ctx_wrap(count_q, conn)
        total = count_result.scalar() or 0

        order_col = _SORT_MAP.get(filter.sort, cards.c.created_at.desc())
        offset = (filter.page - 1) * filter.page_size

        items_q = (
            sa.select(*_LIST_COLS)
            .where(sa.and_(*base_where))
            .order_by(order_col)
            .limit(filter.page_size)
            .offset(offset)
        )
        items_result = await self.ctx_wrap(items_q, conn)
        items = [
            CardListItem.model_validate(row, from_attributes=True)
            for row in items_result.fetchall()
        ]
        return items, total

    async def update(
        self,
        id: UUID,
        data: CardUpdate,
        conn: AsyncConnection | None = None,
    ) -> CardDB | None:
        values = data.model_dump(exclude_unset=True, mode="python")
        if not values:
            return await self.get_by_id(id, conn=conn)

        if "label_set" in values and values["label_set"] is not None:
            values["label_set"] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in values["label_set"]
            ]
        if "contacts" in values and values["contacts"] is not None:
            values["contacts"] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in values["contacts"]
            ]
        for key in ("bg_gradient", "avatar_gradient"):
            if values.get(key) is not None:
                values[key] = normalize_gradient(values[key])

        values["updated_at"] = sa.func.now()
        result = await self.ctx_wrap(
            sa.update(cards)
            .where(cards.c.id == id, cards.c.deleted_at.is_(None))
            .values(**values)
            .returning(cards),
            conn,
        )
        row = result.fetchone()
        return CardDB.model_validate(row, from_attributes=True) if row else None

    async def soft_delete(
        self, id: UUID, acl_filter=None, conn: AsyncConnection | None = None
    ) -> bool:
        q = (
            sa.update(cards)
            .where(cards.c.id == id, cards.c.deleted_at.is_(None))
            .values(deleted_at=sa.func.now(), updated_at=sa.func.now())
            .returning(cards.c.id)
        )
        if acl_filter is not None:
            q = q.where(acl_filter)
        result = await self.ctx_wrap(q, conn)
        return result.fetchone() is not None

    async def reassign_template(
        self, from_id: UUID, to_id: UUID, conn: AsyncConnection | None = None
    ) -> int:
        result = await self.ctx_wrap(
            sa.update(cards)
            .where(cards.c.template_id == from_id, cards.c.deleted_at.is_(None))
            .values(template_id=to_id, updated_at=sa.func.now())
            .returning(cards.c.id),
            conn,
        )
        return len(result.fetchall())

    async def soft_delete_by_template(
        self, template_id: UUID, conn: AsyncConnection | None = None
    ) -> int:
        result = await self.ctx_wrap(
            sa.update(cards)
            .where(cards.c.template_id == template_id, cards.c.deleted_at.is_(None))
            .values(deleted_at=sa.func.now(), updated_at=sa.func.now())
            .returning(cards.c.id),
            conn,
        )
        return len(result.fetchall())

    async def update_slug(self, id: UUID, slug: str, conn: AsyncConnection | None = None) -> None:
        await self.ctx_wrap(
            sa.update(cards)
            .where(cards.c.id == id)
            .values(public_slug=slug, updated_at=sa.func.now()),
            conn,
        )

    async def set_photo_key(
        self, id: UUID, photo_key: str, conn: AsyncConnection | None = None
    ) -> None:
        await self.ctx_wrap(
            sa.update(cards)
            .where(cards.c.id == id)
            .values(photo_key=photo_key, updated_at=sa.func.now()),
            conn,
        )

    async def set_logo_key(
        self, id: UUID, logo_key: str, conn: AsyncConnection | None = None
    ) -> None:
        await self.ctx_wrap(
            sa.update(cards)
            .where(cards.c.id == id)
            .values(logo_key=logo_key, updated_at=sa.func.now()),
            conn,
        )

    async def update_last_opened(self, id: UUID, conn: AsyncConnection | None = None) -> None:
        await self.ctx_wrap(
            sa.update(cards).where(cards.c.id == id).values(last_opened_at=sa.func.now()),
            conn,
        )

    async def slug_exists(self, slug: str, conn: AsyncConnection | None = None) -> bool:
        result = await self.ctx_wrap(
            sa.select(sa.literal(1)).where(cards.c.public_slug == slug).limit(1),
            conn,
        )
        return result.fetchone() is not None

    async def membership_no_exists(
        self,
        membership_no: str,
        *,
        exclude_id: UUID | None = None,
        conn: AsyncConnection | None = None,
    ) -> bool:
        normalized = membership_no.strip()
        q = sa.select(sa.literal(1)).where(
            sa.func.lower(sa.func.trim(cards.c.membership_no)) == normalized.lower(),
            cards.c.deleted_at.is_(None),
        )
        if exclude_id is not None:
            q = q.where(cards.c.id != exclude_id)
        result = await self.ctx_wrap(q.limit(1), conn)
        return result.fetchone() is not None

    async def iter_all_for_export(
        self,
        *,
        filter: CardsListFilter | None = None,
        acl_filter=None,
        batch_size: int = 500,
        conn: AsyncConnection | None = None,
    ):
        """Yield card rows in batches for export.

        Returns dicts with all columns needed by the export view, ordered by
        created_at ASC for stable, resumable iteration. Soft-deleted rows are
        skipped. `filter` — те же условия, что и в списке карточек, чтобы
        выгрузка соответствовала выбранной категории/поиску/датам.
        """
        cols = [
            cards.c.id,
            cards.c.public_slug,
            cards.c.last_name,
            cards.c.first_name,
            cards.c.middle_name,
            cards.c.membership_no,
            cards.c.category_id,
            cards.c.region,
            cards.c.birth_date,
            cards.c.card_issue_date,
            cards.c.join_date,
            cards.c.exclusion_year,
            cards.c.exclusion_date,
            cards.c.death_date,
            cards.c.chairman,
            cards.c.is_active,
            cards.c.created_at,
        ]
        base_where = (
            build_card_filters(filter, acl_filter)
            if filter is not None
            else [cards.c.deleted_at.is_(None)] + ([acl_filter] if acl_filter is not None else [])
        )
        last_created_at = None
        last_id = None
        while True:
            q = (
                sa.select(*cols)
                .where(sa.and_(*base_where))
                .order_by(cards.c.created_at.asc(), cards.c.id.asc())
                .limit(batch_size)
            )
            if last_created_at is not None and last_id is not None:
                q = q.where(
                    sa.or_(
                        cards.c.created_at > last_created_at,
                        sa.and_(
                            cards.c.created_at == last_created_at,
                            cards.c.id > last_id,
                        ),
                    )
                )
            result = await self.ctx_wrap(q, conn)
            rows = result.fetchall()
            if not rows:
                break
            for row in rows:
                yield row._mapping
            last_created_at = rows[-1].created_at
            last_id = rows[-1].id
            if len(rows) < batch_size:
                break
