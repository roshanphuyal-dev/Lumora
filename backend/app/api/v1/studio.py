import uuid

from fastapi import APIRouter, Query, Response, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.course import Page
from app.schemas.generated_material import GeneratedMaterialCreate, GeneratedMaterialRead
from app.services import generated_material_service

router = APIRouter(prefix="/notebooks/{notebook_id}/studio", tags=["studio"])
Limit = Query(default=20, ge=1, le=100)
Offset = Query(default=0, ge=0)


@router.post("", response_model=GeneratedMaterialRead, status_code=status.HTTP_201_CREATED)
async def create_generated_material(
    notebook_id: uuid.UUID,
    payload: GeneratedMaterialCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> GeneratedMaterialRead:
    material = await generated_material_service.create_generated_material(
        db, current_user.id, notebook_id, payload
    )
    return GeneratedMaterialRead.model_validate(material)


@router.get("", response_model=Page[GeneratedMaterialRead])
async def list_generated_materials(
    notebook_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Limit,
    offset: int = Offset,
) -> Page[GeneratedMaterialRead]:
    page = await generated_material_service.list_generated_materials(
        db, current_user.id, notebook_id, limit, offset
    )
    return Page[GeneratedMaterialRead](
        items=[GeneratedMaterialRead.model_validate(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{material_id}", response_model=GeneratedMaterialRead)
async def get_generated_material(
    notebook_id: uuid.UUID,
    material_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> GeneratedMaterialRead:
    material = await generated_material_service.get_owned_generated_material(
        db, current_user.id, notebook_id, material_id
    )
    return GeneratedMaterialRead.model_validate(material)


@router.get("/{material_id}/download")
async def download_generated_material(
    notebook_id: uuid.UUID,
    material_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    content, mime_type, filename = await generated_material_service.get_generated_material_file(
        db, current_user.id, notebook_id, material_id
    )
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generated_material(
    notebook_id: uuid.UUID,
    material_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    await generated_material_service.delete_generated_material(
        db, current_user.id, notebook_id, material_id
    )
