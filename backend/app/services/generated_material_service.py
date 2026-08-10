import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_file_storage
from app.models.generated_material import GeneratedMaterial, MaterialArtifactType, MaterialStatus
from app.models.notebook import NotebookSourceIndexStatus
from app.schemas.course import PageResult
from app.schemas.generated_material import GeneratedMaterialCreate
from app.services.notebook_service import get_owned_notebook
from app.workers.studio_tasks import generate_studio_artifact_task

_FILE_SUFFIXES = {
    MaterialArtifactType.AUDIO: ".mp3",
    MaterialArtifactType.SLIDES: ".pdf",
    MaterialArtifactType.INFOGRAPHIC: ".png",
    MaterialArtifactType.DATA_TABLE: ".csv",
}


async def create_generated_material(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    payload: GeneratedMaterialCreate,
) -> GeneratedMaterial:
    notebook = await get_owned_notebook(db, user_id, notebook_id)
    has_indexed_source = any(
        source.indexing_status == NotebookSourceIndexStatus.INDEXED for source in notebook.sources
    )
    if not notebook.notebooklm_notebook_id or not has_indexed_source:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This notebook has no indexed sources yet — add and index a source before "
                "generating Studio artifacts."
            ),
        )
    if payload.artifact_type == MaterialArtifactType.DATA_TABLE and not (
        payload.description and payload.description.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="data_table artifacts require a description of what to extract.",
        )

    options = payload.model_dump(exclude={"artifact_type", "title"}, exclude_none=True)
    artifact_type = MaterialArtifactType(payload.artifact_type)
    material = GeneratedMaterial(
        notebook_id=notebook_id,
        user_id=user_id,
        artifact_type=artifact_type,
        status=MaterialStatus.PENDING,
        title=payload.title or f"{artifact_type.value.replace('_', ' ').title()} — {notebook.name}",
        options=options,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)
    generate_studio_artifact_task.delay(str(material.id))
    return material


async def list_generated_materials(
    db: AsyncSession, user_id: uuid.UUID, notebook_id: uuid.UUID, limit: int, offset: int
) -> PageResult[GeneratedMaterial]:
    await get_owned_notebook(db, user_id, notebook_id)
    filters = [
        GeneratedMaterial.notebook_id == notebook_id,
        GeneratedMaterial.user_id == user_id,
    ]
    total = await db.scalar(select(func.count()).select_from(GeneratedMaterial).where(*filters))
    result = await db.scalars(
        select(GeneratedMaterial)
        .where(*filters)
        .order_by(GeneratedMaterial.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return PageResult(items=list(result), total=total or 0, limit=limit, offset=offset)


async def get_owned_generated_material(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    material_id: uuid.UUID,
) -> GeneratedMaterial:
    material = await db.scalar(
        select(GeneratedMaterial).where(
            GeneratedMaterial.id == material_id,
            GeneratedMaterial.notebook_id == notebook_id,
            GeneratedMaterial.user_id == user_id,
        )
    )
    if material is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Generated material not found"
        )
    return material


async def delete_generated_material(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    material_id: uuid.UUID,
) -> None:
    material = await get_owned_generated_material(db, user_id, notebook_id, material_id)
    await db.delete(material)
    await db.commit()


async def get_generated_material_file(
    db: AsyncSession,
    user_id: uuid.UUID,
    notebook_id: uuid.UUID,
    material_id: uuid.UUID,
) -> tuple[bytes, str, str]:
    material = await get_owned_generated_material(db, user_id, notebook_id, material_id)
    if material.storage_path is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This material has no downloadable file.",
        )
    content = await get_file_storage().download(material.storage_path)
    suffix = _FILE_SUFFIXES[material.artifact_type]
    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "-", material.title).strip("-.") or "material"
    return content, material.mime_type or "application/octet-stream", f"{safe_title}{suffix}"
