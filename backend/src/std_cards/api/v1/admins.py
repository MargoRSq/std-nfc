from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from std_cards.api.deps import AdminServiceDep, AuditRepoDep, SuperAdminDep
from std_cards.models.admin import AdminInvite, AdminListItem, AdminUpdate
from std_cards.models.audit import AuditLogEntry
from std_cards.models.auth import UserPublic

router = APIRouter(prefix="/api/admins", tags=["admins"])


@router.get("/")
async def list_admins(
    user: SuperAdminDep,
    service: AdminServiceDep,
) -> list[AdminListItem]:
    return await service.list_admins()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_admin(
    body: AdminInvite,
    user: SuperAdminDep,
    service: AdminServiceDep,
) -> dict:
    new_user, temp_password = await service.create_admin(body, actor=user)
    return {
        "user": UserPublic.model_validate(new_user, from_attributes=True).model_dump(mode="json"),
        "temporary_password": temp_password,
    }


@router.patch("/{admin_id}")
async def update_admin(
    admin_id: UUID,
    body: AdminUpdate,
    user: SuperAdminDep,
    service: AdminServiceDep,
) -> UserPublic:
    updated = await service.update_admin(admin_id, body, actor=user)
    return UserPublic.model_validate(updated, from_attributes=True)


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin(
    admin_id: UUID,
    user: SuperAdminDep,
    service: AdminServiceDep,
) -> Response:
    await service.delete_admin(admin_id, actor=user)
    return Response(status_code=204)


@router.post("/{admin_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    admin_id: UUID,
    user: SuperAdminDep,
    service: AdminServiceDep,
) -> dict:
    new_pw = await service.reset_password(admin_id, actor=user)
    return {"temporary_password": new_pw}


@router.post("/{admin_id}/reset-2fa", status_code=status.HTTP_204_NO_CONTENT)
async def reset_2fa(
    admin_id: UUID,
    user: SuperAdminDep,
    service: AdminServiceDep,
) -> Response:
    await service.reset_2fa(admin_id, actor=user)
    return Response(status_code=204)


@router.post("/{admin_id}/force-logout", status_code=status.HTTP_204_NO_CONTENT)
async def force_logout(
    admin_id: UUID,
    user: SuperAdminDep,
    service: AdminServiceDep,
) -> Response:
    await service.force_logout(admin_id, actor=user)
    return Response(status_code=204)


@router.get("/audit")
async def audit_log(
    user: SuperAdminDep,
    audit: AuditRepoDep,
    actor_id: UUID | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    ts_from: datetime | None = Query(None),
    ts_to: datetime | None = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict:
    entries, total = await audit.list_with_filters(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        ts_from=ts_from,
        ts_to=ts_to,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [
            AuditLogEntry.model_validate(e, from_attributes=True).model_dump(mode="json")
            for e in entries
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
