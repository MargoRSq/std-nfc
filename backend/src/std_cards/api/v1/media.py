from uuid import UUID

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import Response

from std_cards.api.deps import AdminDep, MediaServiceDep
from std_cards.core.uploads import read_upload_capped

router = APIRouter(tags=["media"])


@router.post("/api/cards/{card_id}/photo", status_code=200)
async def upload_photo(
    card_id: UUID,
    user: AdminDep,
    service: MediaServiceDep,
    file: UploadFile = File(...),
) -> dict:
    raw = await read_upload_capped(file, 10 * 1024 * 1024)
    key = await service.upload_card_photo(card_id, raw, file.content_type or "image/jpeg")
    return {"photo_key": key}


@router.post("/api/cards/{card_id}/logo", status_code=200)
async def upload_logo(
    card_id: UUID,
    user: AdminDep,
    service: MediaServiceDep,
    file: UploadFile = File(...),
) -> dict:
    raw = await read_upload_capped(file, 5 * 1024 * 1024)
    key = await service.upload_card_logo(card_id, raw, file.content_type or "image/jpeg")
    return {"logo_key": key}


@router.get("/api/media/{key:path}", include_in_schema=False)
async def get_media(key: str, service: MediaServiceDep) -> Response:
    data, content_type = await service.stream_media(key)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
