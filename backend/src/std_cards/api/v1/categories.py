from fastapi import APIRouter

from std_cards.api.deps import CategoryRepoDep, ViewerDep
from std_cards.models.card import CategoryDB

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/")
async def list_categories(
    _user: ViewerDep,
    repo: CategoryRepoDep,
) -> list[CategoryDB]:
    return await repo.list_all()
