from fastapi import APIRouter

from std_cards.api.deps import CategoryRepoDep, SuperAdminDep, ViewerDep
from std_cards.core.exceptions import NotFoundError
from std_cards.models.card import CategoryDB, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/")
async def list_categories(
    _user: ViewerDep,
    repo: CategoryRepoDep,
) -> list[CategoryDB]:
    return await repo.list_all()


@router.patch("/{id}")
async def update_category(
    id: int,
    body: CategoryUpdate,
    _user: SuperAdminDep,
    repo: CategoryRepoDep,
) -> CategoryDB:
    updated = await repo.update(id, body)
    if updated is None:
        raise NotFoundError(message="Категория не найдена")
    return updated
