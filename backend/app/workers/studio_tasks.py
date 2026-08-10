import asyncio
import logging
import tempfile
import time
import uuid
from pathlib import Path

from ai.notebooklm.client import NotebookLMClient, NotebookLMError
from ai.orchestrator.orchestrator import run_task
from ai.orchestrator.schemas import StudioArtifactCreateRequest
from ai.orchestrator.task_types import TaskType

from app.core.storage import get_file_storage
from app.db.session import celery_session_maker
from app.models.generated_material import GeneratedMaterial, MaterialArtifactType, MaterialStatus
from app.models.notebook import Notebook
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 10
_MAX_WAIT_SECONDS = {
    "report": 300,
    "infographic": 300,
    "slides": 480,
    "data_table": 300,
    "audio": 720,
}
_FILE_DETAILS = {
    MaterialArtifactType.REPORT: (".md", None),
    MaterialArtifactType.AUDIO: (".mp3", "audio/mpeg"),
    MaterialArtifactType.SLIDES: (".pdf", "application/pdf"),
    MaterialArtifactType.INFOGRAPHIC: (".png", "image/png"),
    MaterialArtifactType.DATA_TABLE: (".csv", "text/csv"),
}


class StudioArtifactTimeoutError(RuntimeError):
    pass


@celery_app.task(name="studio.generate", time_limit=900)
def generate_studio_artifact_task(material_id: str) -> None:
    asyncio.run(_generate_studio_artifact(uuid.UUID(material_id)))


async def _generate_studio_artifact(material_id: uuid.UUID) -> None:
    async with celery_session_maker() as db:
        material = await db.get(GeneratedMaterial, material_id)
        if material is None:
            return
        material.status = MaterialStatus.GENERATING
        material.error_message = None
        await db.commit()

        tmp_path: Path | None = None
        try:
            notebook = await db.get(Notebook, material.notebook_id)
            if notebook is None or notebook.notebooklm_notebook_id is None:
                raise RuntimeError("The material's NotebookLM notebook is unavailable")

            response = await run_task(
                TaskType.STUDIO_ARTIFACT_CREATE,
                StudioArtifactCreateRequest(
                    artifact_type=material.artifact_type.value,
                    notebooklm_notebook_id=notebook.notebooklm_notebook_id,
                    options=material.options,
                ),
            )
            artifact_id = response.metadata["notebooklm_artifact_id"]
            material.notebooklm_artifact_id = artifact_id
            await db.commit()

            if material.artifact_type is MaterialArtifactType.MINDMAP:
                material.content = response.content
                material.status = MaterialStatus.DONE
                await db.commit()
                return

            client = NotebookLMClient()
            remote_status = response.metadata["status"]
            max_wait = _MAX_WAIT_SECONDS[material.artifact_type.value]
            started_at = time.monotonic()
            while remote_status not in {"completed", "failed"}:
                elapsed = time.monotonic() - started_at
                if elapsed >= max_wait:
                    raise StudioArtifactTimeoutError(
                        f"Studio artifact did not complete within the expected time ({max_wait}s)"
                    )
                await asyncio.sleep(min(_POLL_INTERVAL_SECONDS, max_wait - elapsed))
                remote_status = await client.get_studio_artifact_status(
                    notebooklm_notebook_id=notebook.notebooklm_notebook_id,
                    artifact_id=artifact_id,
                )

            if remote_status == "failed":
                raise NotebookLMError("NotebookLM failed to generate the Studio artifact")

            suffix, mime_type = _FILE_DETAILS[material.artifact_type]
            tmp_path = _empty_temp_file(suffix)
            await client.download_studio_artifact(
                notebooklm_notebook_id=notebook.notebooklm_notebook_id,
                artifact_type=material.artifact_type.value,
                artifact_id=artifact_id,
                output_path=str(tmp_path),
            )
            if material.artifact_type is MaterialArtifactType.REPORT:
                material.content = await asyncio.to_thread(tmp_path.read_text)
            else:
                content = await asyncio.to_thread(tmp_path.read_bytes)
                storage_path = f"generated_materials/{material.id}{suffix}"
                await get_file_storage().upload(storage_path, content)
                material.storage_path = storage_path
                material.mime_type = mime_type
            material.status = MaterialStatus.DONE
            await db.commit()
        except Exception as exc:
            logger.exception("Failed to generate Studio artifact %s", material_id)
            material.status = MaterialStatus.FAILED
            material.error_message = str(exc)
            await db.commit()
        finally:
            if tmp_path is not None:
                await asyncio.to_thread(tmp_path.unlink, missing_ok=True)


def _empty_temp_file(suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        return Path(tmp.name)
