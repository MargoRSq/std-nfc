from typing import Literal
from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel

from std_cards.api.deps import AdminDep, TemplateServiceDep
from std_cards.models.template import TemplateCreate, TemplateDB, TemplateUpdate

router = APIRouter(prefix="/api/templates", tags=["templates"])


class DuplicateRequest(BaseModel):
    new_name: str


class FromCardRequest(BaseModel):
    name: str


@router.get("/")
async def list_templates(
    _user: AdminDep,
    svc: TemplateServiceDep,
) -> list[TemplateDB]:
    return await svc.list_all()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreate,
    user: AdminDep,
    svc: TemplateServiceDep,
) -> TemplateDB:
    return await svc.create(body, created_by=user.id)


@router.get("/{id}")
async def get_template(
    id: UUID,
    _user: AdminDep,
    svc: TemplateServiceDep,
) -> TemplateDB:
    return await svc.get(id)


@router.patch("/{id}")
async def update_template(
    id: UUID,
    body: TemplateUpdate,
    _user: AdminDep,
    svc: TemplateServiceDep,
) -> TemplateDB:
    return await svc.update(id, body)


@router.delete("/{id}")
async def delete_template(
    id: UUID,
    _user: AdminDep,
    svc: TemplateServiceDep,
    cascade: Literal["template_only", "with_cards"] = "template_only",
) -> dict:
    return await svc.delete(id, cascade=cascade)


@router.post("/{id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_template(
    id: UUID,
    body: DuplicateRequest,
    _user: AdminDep,
    svc: TemplateServiceDep,
) -> TemplateDB:
    return await svc.duplicate(id, body.new_name)


@router.post("/from-card/{card_id}", status_code=status.HTTP_201_CREATED)
async def template_from_card(
    card_id: UUID,
    body: FromCardRequest,
    user: AdminDep,
    svc: TemplateServiceDep,
) -> TemplateDB:
    return await svc.from_card(card_id, body.name, created_by=user.id)
