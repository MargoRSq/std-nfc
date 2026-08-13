from fastapi import APIRouter, Response, status

from std_cards.api.deps import AdminDep, RegionContactsRepoDep, ViewerDep
from std_cards.core.exceptions import NotFoundError, ValidationFailedError
from std_cards.models.region_contacts import RegionContactsDB, RegionContactsUpsert

router = APIRouter(prefix="/api/region-contacts", tags=["region-contacts"])


@router.get("/")
async def list_region_contacts(
    _user: ViewerDep,
    repo: RegionContactsRepoDep,
) -> list[RegionContactsDB]:
    return await repo.list_all()


@router.put("/{region}")
async def upsert_region_contacts(
    region: str,
    body: RegionContactsUpsert,
    _user: AdminDep,
    repo: RegionContactsRepoDep,
) -> RegionContactsDB:
    region = region.strip()
    if not region:
        raise ValidationFailedError(message="Регион не задан")
    return await repo.upsert(region, body)


@router.delete("/{region}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_region_contacts(
    region: str,
    _user: AdminDep,
    repo: RegionContactsRepoDep,
) -> Response:
    if not await repo.delete(region.strip()):
        raise NotFoundError(message="Контакты региона не найдены")
    return Response(status_code=204)
