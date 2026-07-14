from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import Response

from std_cards.api.deps import (
    AdminDep,
    AuditRepoDep,
    CardMessageServiceDep,
    CardServiceDep,
)
from std_cards.core.uploads import read_upload_capped
from std_cards.models.audit import AuditAction
from std_cards.models.card import CardUpdate
from std_cards.models.card_message import CardMessageCreate, CardMessageDB

router = APIRouter(prefix="/api/cards/{card_id}/messages", tags=["card-messages"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def publish_message(
    card_id: UUID,
    user: AdminDep,
    svc: CardMessageServiceDep,
    card_svc: CardServiceDep,
    audit: AuditRepoDep,
    text: str = Form(..., max_length=2000),
    file: UploadFile | None = File(None),
    deactivate: bool = Form(True),
) -> CardMessageDB:
    await card_svc.get(card_id, current_user=user)  # ACL: 404 if card outside caller's scope
    image_key: str | None = None
    if file is not None and file.filename:
        raw = await read_upload_capped(file, 5 * 1024 * 1024)
        image_key = await svc.upload_image(card_id, raw, file.content_type or "image/jpeg")

    msg = await svc.create_message(
        card_id,
        CardMessageCreate(text=text, image_key=image_key),
        actor_id=user.id,
    )
    if deactivate:
        await card_svc.update(card_id, CardUpdate(is_active=False), current_user=user)
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_UPDATE,
        entity_type="card_message",
        entity_id=str(msg.id),
        diff={
            "card_id": str(card_id),
            "has_image": image_key is not None,
            "deactivated": deactivate,
        },
    )
    return msg


@router.get("")
async def list_messages(
    card_id: UUID,
    user: AdminDep,
    svc: CardMessageServiceDep,
    card_svc: CardServiceDep,
) -> list[CardMessageDB]:
    await card_svc.get(card_id, current_user=user)  # ACL: 404 if card outside caller's scope
    return await svc.list_for_card(card_id)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    card_id: UUID,
    message_id: UUID,
    user: AdminDep,
    svc: CardMessageServiceDep,
    card_svc: CardServiceDep,
    audit: AuditRepoDep,
) -> Response:
    await card_svc.get(card_id, current_user=user)  # ACL: 404 if card outside caller's scope
    await svc.delete_message(card_id, message_id)
    reactivated = False
    remaining = await svc.list_for_card(card_id)
    if not remaining:
        card = await card_svc.get(card_id, current_user=user)
        if not card.is_active:
            await card_svc.update(card_id, CardUpdate(is_active=True), current_user=user)
            reactivated = True
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_UPDATE,
        entity_type="card_message",
        entity_id=str(message_id),
        diff={"card_id": str(card_id), "deleted": True, "reactivated": reactivated},
    )
    return Response(status_code=204)
