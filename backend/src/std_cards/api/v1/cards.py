from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from std_cards.api.deps import (
    AdminDep,
    AuditRepoDep,
    CardServiceDep,
    SuperAdminDep,
    get_card_service,
    require_admin,
)
from std_cards.models.audit import AuditAction
from std_cards.models.card import CardCreate, CardDB, CardsList, CardsListFilter, CardUpdate
from std_cards.services.card_service import CardService

router = APIRouter(prefix="/api/cards", tags=["cards"])


class RegenerateSlugRequest(BaseModel):
    custom: str | None = None


class SlugAvailableResponse(BaseModel):
    available: bool


class ApplyTemplateRequest(BaseModel):
    template_id: UUID


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_card(
    body: CardCreate,
    user: AdminDep,
    svc: CardServiceDep,
    audit: AuditRepoDep,
) -> CardDB:
    card = await svc.create(body, created_by=user.id)
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_CREATE,
        entity_type="card",
        entity_id=str(card.id),
        diff=body.model_dump(mode="json"),
    )
    return card


@router.post("/preview", include_in_schema=False)
async def preview_card(
    body: CardCreate,
    request: Request,
    _user: AdminDep,
) -> Response:
    """Render the public card template against draft data without persisting."""
    from fastapi.responses import HTMLResponse

    from std_cards.api.v1.public import _safe_bg
    from std_cards.core.color import contrast_palette
    from std_cards.core.templating import render

    card_data = body.model_dump(mode="python")
    card_data.setdefault("public_slug", "preview")
    card_data.setdefault("is_active", True)
    card_data, bg_for_palette = _safe_bg(card_data)
    palette = contrast_palette(bg_for_palette)
    html = render(
        "card.html",
        card=card_data,
        slug=card_data["public_slug"],
        palette=palette,
        message=None,
        show_close=False,
        updated_unix=0,
    )

    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    if host:
        base_tag = f'<base href="{proto}://{host}/">'
        html = html.replace("<head>", f"<head>{base_tag}", 1)

    return HTMLResponse(
        content=html,
        status_code=200,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "X-Frame-Options": "SAMEORIGIN",
        },
    )


@router.get("/export.xlsx")
async def export_cards_xlsx(
    user: SuperAdminDep,
    svc: CardServiceDep,
    audit: AuditRepoDep,
) -> StreamingResponse:
    content, row_count = await svc.export_all_xlsx()
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_BULK_EXPORT,
        entity_type="cards",
        diff={"format": "xlsx", "row_count": row_count},
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=cards-export.xlsx",
            "Content-Length": str(len(content)),
        },
    )


@router.get("/check-slug")
async def check_slug(
    _user: Annotated[None, Depends(require_admin)],
    svc: Annotated[CardService, Depends(get_card_service)],
    slug: str = Query(..., min_length=3, max_length=32),
    exclude_id: UUID | None = Query(None),
) -> SlugAvailableResponse:
    available = await svc.check_slug(slug, exclude_id=exclude_id)
    return SlugAvailableResponse(available=available)


_DATE_FIELDS = {"added", "opened", "modified", "created", "issued"}


@router.get("/")
async def list_cards(
    user: AdminDep,
    svc: CardServiceDep,
    q: str | None = Query(None),
    category_id: int | None = Query(None),
    region: str | None = Query(None),
    date_field: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort: str = Query(default="-created_at"),
) -> CardsList:
    from std_cards.core.exceptions import ValidationFailedError

    if date_field is not None and date_field not in _DATE_FIELDS:
        raise ValidationFailedError(
            message=f"Invalid date_field, must be one of: {sorted(_DATE_FIELDS)}"
        )

    parsed_from = date.fromisoformat(date_from) if date_from else None
    parsed_to = date.fromisoformat(date_to) if date_to else None
    if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
        raise ValidationFailedError(message="date_from must be on or before date_to")

    filter = CardsListFilter(
        q=q,
        category_id=category_id,
        region=region,
        date_field=date_field,  # type: ignore[arg-type]
        date_from=parsed_from,
        date_to=parsed_to,
        is_active=is_active,
        page=page,
        page_size=page_size,
        sort=sort,  # type: ignore[arg-type]
    )
    return await svc.list(filter, current_user=user)


@router.get("/{id}")
async def get_card(
    id: UUID,
    user: AdminDep,
    svc: CardServiceDep,
) -> CardDB:
    return await svc.get(id, current_user=user)


@router.patch("/{id}")
async def update_card(
    id: UUID,
    body: CardUpdate,
    user: AdminDep,
    svc: CardServiceDep,
    audit: AuditRepoDep,
) -> CardDB:
    card = await svc.update(id, body, current_user=user)
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_UPDATE,
        entity_type="card",
        entity_id=str(id),
        diff=body.model_dump(mode="json", exclude_unset=True),
    )
    return card


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    id: UUID,
    user: AdminDep,
    svc: CardServiceDep,
    audit: AuditRepoDep,
) -> Response:
    await svc.delete(id, current_user=user)
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_DELETE,
        entity_type="card",
        entity_id=str(id),
    )
    return Response(status_code=204)


@router.post("/{id}/regenerate-slug")
async def regenerate_slug(
    id: UUID,
    body: RegenerateSlugRequest,
    _user: SuperAdminDep,
    svc: CardServiceDep,
) -> dict:
    new_slug = await svc.regenerate_slug(id, custom=body.custom)
    return {"public_slug": new_slug}


@router.post("/{id}/apply-template")
async def apply_template(
    id: UUID,
    body: ApplyTemplateRequest,
    user: AdminDep,
    svc: CardServiceDep,
    audit: AuditRepoDep,
) -> CardDB:
    card = await svc.apply_template(id, body.template_id, current_user=user)
    await audit.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_UPDATE,
        entity_type="card",
        entity_id=str(card.id),
        diff={"template_id": str(body.template_id)},
    )
    return card
