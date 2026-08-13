import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import region_contacts
from std_cards.models.card import ContactBlock
from std_cards.models.region_contacts import RegionContactsDB, RegionContactsUpsert


class RegionContactsRepository(BaseRepository):
    async def list_all(self, conn: AsyncConnection | None = None) -> list[RegionContactsDB]:
        result = await self.ctx_wrap(
            sa.select(region_contacts).order_by(region_contacts.c.region),
            conn,
        )
        return [
            RegionContactsDB.model_validate(row, from_attributes=True) for row in result.fetchall()
        ]

    async def get(
        self, region: str, conn: AsyncConnection | None = None
    ) -> RegionContactsDB | None:
        result = await self.ctx_wrap(
            sa.select(region_contacts).where(region_contacts.c.region == region),
            conn,
        )
        row = result.fetchone()
        return RegionContactsDB.model_validate(row, from_attributes=True) if row else None

    async def upsert(
        self,
        region: str,
        data: RegionContactsUpsert,
        conn: AsyncConnection | None = None,
    ) -> RegionContactsDB:
        contacts = [b.model_dump() for b in data.contacts]
        stmt = (
            pg_insert(region_contacts)
            .values(region=region, contacts=contacts)
            .on_conflict_do_update(
                index_elements=[region_contacts.c.region],
                set_={"contacts": contacts, "updated_at": sa.func.now()},
            )
            .returning(region_contacts)
        )
        result = await self.ctx_wrap(stmt, conn)
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert region contacts")
        return RegionContactsDB.model_validate(row, from_attributes=True)

    async def delete(self, region: str, conn: AsyncConnection | None = None) -> bool:
        result = await self.ctx_wrap(
            sa.delete(region_contacts)
            .where(region_contacts.c.region == region)
            .returning(region_contacts.c.id),
            conn,
        )
        return result.fetchone() is not None

    async def resolve(
        self, region: str | None, conn: AsyncConnection | None = None
    ) -> list[ContactBlock]:
        """Контакты региона, иначе дефолтные («*»)."""
        wanted = [r for r in (region, "*") if r]
        result = await self.ctx_wrap(
            sa.select(region_contacts).where(region_contacts.c.region.in_(wanted)),
            conn,
        )
        by_region = {row.region: row.contacts for row in result.fetchall()}
        raw = by_region.get(region or "") or by_region.get("*") or []
        return [ContactBlock.model_validate(b) for b in raw]
