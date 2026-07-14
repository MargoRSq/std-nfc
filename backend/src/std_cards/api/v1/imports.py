from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from std_cards.api.deps import AdminDep, ImportServiceDep
from std_cards.core.exceptions import NotFoundError
from std_cards.models.import_job import ImportJobDB

router = APIRouter(prefix="/api/import", tags=["import"])


@router.get("/empty-template.xlsx")
async def download_empty_template(
    _user: AdminDep,
    svc: ImportServiceDep,
) -> StreamingResponse:
    content = svc.generate_empty_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=import-template.xlsx"},
    )


@router.post("/excel", status_code=status.HTTP_201_CREATED)
async def upload_excel(
    user: AdminDep,
    svc: ImportServiceDep,
    file: UploadFile = File(...),
    template_id: UUID | None = Form(None),
) -> ImportJobDB:
    file_bytes = await file.read()
    file_name = file.filename or "import.xlsx"
    return await svc.upload_and_enqueue(
        file_bytes=file_bytes,
        file_name=file_name,
        template_id=template_id,
        created_by=user.id,
    )


@router.get("/jobs")
async def list_jobs(
    user: AdminDep,
    svc: ImportServiceDep,
) -> list[ImportJobDB]:
    return await svc.imports.list_for_user(user.id)


@router.get("/jobs/{id}")
async def get_job(
    id: UUID,
    _user: AdminDep,
    svc: ImportServiceDep,
) -> ImportJobDB:
    job = await svc.imports.get_by_id(id)
    if job is None:
        raise NotFoundError()
    return job


@router.post("/jobs/{id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    id: UUID,
    _user: AdminDep,
    svc: ImportServiceDep,
) -> Response:
    await svc.cancel(id)
    return Response(status_code=204)
