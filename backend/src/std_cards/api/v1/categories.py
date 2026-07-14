from fastapi import APIRouter

from std_cards.api.deps import AdminDep, CategoryRepoDep
from std_cards.models.card import CategoryDB

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/")
async def list_categories(
    _user: AdminDep,
    repo: CategoryRepoDep,
) -> list[CategoryDB]:
    return await repo.list_all()
