from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy.exc import IntegrityError

from std_cards.api.deps import AdminDep, LabelPresetRepoDep
from std_cards.core.exceptions import ConflictError, NotFoundError
from std_cards.models.label_preset import (
    LabelPresetCreate,
    LabelPresetDB,
    LabelPresetReorder,
    LabelPresetUpdate,
)

router = APIRouter(prefix="/api/label-presets", tags=["label-presets"])


@router.get("/")
async def list_label_presets(
    user: AdminDep,
    repo: LabelPresetRepoDep,
) -> list[LabelPresetDB]:
    return await repo.list_by_admin(user.id)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_label_preset(
    body: LabelPresetCreate,
    user: AdminDep,
    repo: LabelPresetRepoDep,
) -> LabelPresetDB:
    try:
        return await repo.create(user.id, body)
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "uq_label_presets_admin_name" or "uq_label_presets_admin_name" in str(
            exc.orig or exc
        ):
            raise ConflictError(
                message="Этикетка с таким названием уже существует",
                details={"field": "name"},
            ) from exc
        raise


@router.patch("/{preset_id}")
async def update_label_preset(
    preset_id: UUID,
    body: LabelPresetUpdate,
    user: AdminDep,
    repo: LabelPresetRepoDep,
) -> LabelPresetDB:
    try:
        updated = await repo.update(preset_id, user.id, body)
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "uq_label_presets_admin_name" or "uq_label_presets_admin_name" in str(
            exc.orig or exc
        ):
            raise ConflictError(
                message="Этикетка с таким названием уже существует",
                details={"field": "name"},
            ) from exc
        raise
    if updated is None:
        raise NotFoundError(message="Этикетка не найдена")
    return updated


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label_preset(
    preset_id: UUID,
    user: AdminDep,
    repo: LabelPresetRepoDep,
) -> Response:
    ok = await repo.delete(preset_id, user.id)
    if not ok:
        raise NotFoundError(message="Этикетка не найдена")
    return Response(status_code=204)


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_label_presets(
    body: LabelPresetReorder,
    user: AdminDep,
    repo: LabelPresetRepoDep,
) -> Response:
    await repo.reorder(user.id, body.ids)
    return Response(status_code=204)
