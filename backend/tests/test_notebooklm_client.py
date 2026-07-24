"""Unit tests for `ai/notebooklm/client.py:NotebookLMClient`.

Per `.claude/rules/testing.md`: the `nlm` CLI is an external, costly-to-call
dependency (real NotebookLM calls), so `asyncio.create_subprocess_exec` and
`shutil.which` are mocked -- but the client's own argv-building, JSON parsing,
and error-classification logic all run for real, nothing about `NotebookLMClient`
itself is mocked or skipped.
"""

from unittest.mock import AsyncMock, patch

import pytest
from ai.notebooklm.client import (
    DocumentIndexResult,
    NotebookLMClient,
    NotebookLMError,
)


def _mock_proc(*, returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> AsyncMock:
    proc = AsyncMock()
    proc.communicate.return_value = (stdout, stderr)
    proc.returncode = returncode
    return proc


# --- ensure_remote_notebook ---------------------------------------------------


async def test_ensure_remote_notebook_reuses_existing_id_without_subprocess() -> None:
    client = NotebookLMClient()

    with patch("ai.notebooklm.client.asyncio.create_subprocess_exec") as mock_exec:
        result = await client.ensure_remote_notebook(
            notebooklm_notebook_id="existing-nb-1", name="Biology 101"
        )

    assert result == "existing-nb-1"
    mock_exec.assert_not_called()


async def test_ensure_remote_notebook_creates_new_when_id_is_none() -> None:
    client = NotebookLMClient()
    proc = _mock_proc(returncode=0, stdout=b'{"id": "new-nb-1"}')

    with (
        patch("ai.notebooklm.client.shutil.which", return_value="/usr/bin/nlm"),
        patch(
            "ai.notebooklm.client.asyncio.create_subprocess_exec", return_value=proc
        ) as mock_exec,
    ):
        result = await client.ensure_remote_notebook(
            notebooklm_notebook_id=None, name="Biology 101"
        )

    assert result == "new-nb-1"
    mock_exec.assert_awaited_once_with(
        "nlm",
        "notebook",
        "create",
        "Biology 101",
        "--json",
        stdout=-1,
        stderr=-1,
    )


async def test_ensure_remote_notebook_raises_when_id_missing_from_response() -> None:
    client = NotebookLMClient()
    proc = _mock_proc(returncode=0, stdout=b'{"ok": true}')

    with (
        patch("ai.notebooklm.client.shutil.which", return_value="/usr/bin/nlm"),
        patch("ai.notebooklm.client.asyncio.create_subprocess_exec", return_value=proc),
    ):
        with pytest.raises(NotebookLMError, match="no notebook id"):
            await client.ensure_remote_notebook(notebooklm_notebook_id=None, name="Biology 101")


# --- index_document ------------------------------------------------------------


async def test_index_document_happy_path_parses_result_and_argv() -> None:
    client = NotebookLMClient()
    proc = _mock_proc(returncode=0, stdout=b'{"id": "src-1", "status": "indexed"}')

    with (
        patch("ai.notebooklm.client.shutil.which", return_value="/usr/bin/nlm"),
        patch(
            "ai.notebooklm.client.asyncio.create_subprocess_exec", return_value=proc
        ) as mock_exec,
    ):
        result = await client.index_document(
            notebooklm_notebook_id="nb-1", file_path="/tmp/notes.pdf"
        )

    assert result == DocumentIndexResult(notebooklm_source_id="src-1", status="indexed")
    mock_exec.assert_awaited_once_with(
        "nlm",
        "source",
        "add",
        "nb-1",
        "--file",
        "/tmp/notes.pdf",
        "--wait",
        "--json",
        stdout=-1,
        stderr=-1,
    )


async def test_index_document_defaults_status_to_indexed_when_absent() -> None:
    client = NotebookLMClient()
    proc = _mock_proc(returncode=0, stdout=b'{"id": "src-1"}')

    with (
        patch("ai.notebooklm.client.shutil.which", return_value="/usr/bin/nlm"),
        patch("ai.notebooklm.client.asyncio.create_subprocess_exec", return_value=proc),
    ):
        result = await client.index_document(
            notebooklm_notebook_id="nb-1", file_path="/tmp/notes.pdf"
        )

    assert result.status == "indexed"


async def test_index_document_raises_when_source_id_missing_from_response() -> None:
    client = NotebookLMClient()
    proc = _mock_proc(returncode=0, stdout=b'{"status": "indexed"}')

    with (
        patch("ai.notebooklm.client.shutil.which", return_value="/usr/bin/nlm"),
        patch("ai.notebooklm.client.asyncio.create_subprocess_exec", return_value=proc),
    ):
        with pytest.raises(NotebookLMError, match="no source id"):
            await client.index_document(notebooklm_notebook_id="nb-1", file_path="/tmp/notes.pdf")


# --- error paths shared by both public methods ----------------------------------


async def test_binary_not_found_raises_actionable_error() -> None:
    client = NotebookLMClient()

    with patch("ai.notebooklm.client.shutil.which", return_value=None):
        with pytest.raises(NotebookLMError, match="not found on PATH"):
            await client.index_document(notebooklm_notebook_id="nb-1", file_path="/tmp/notes.pdf")


async def test_nonzero_exit_surfaces_stderr() -> None:
    client = NotebookLMClient()
    proc = _mock_proc(returncode=1, stdout=b"", stderr=b"not authenticated, run nlm login")

    with (
        patch("ai.notebooklm.client.shutil.which", return_value="/usr/bin/nlm"),
        patch("ai.notebooklm.client.asyncio.create_subprocess_exec", return_value=proc),
    ):
        with pytest.raises(NotebookLMError, match="not authenticated, run nlm login"):
            await client.index_document(notebooklm_notebook_id="nb-1", file_path="/tmp/notes.pdf")


async def test_non_json_stdout_raises_notebooklm_error() -> None:
    client = NotebookLMClient()
    proc = _mock_proc(returncode=0, stdout=b"not json at all")

    with (
        patch("ai.notebooklm.client.shutil.which", return_value="/usr/bin/nlm"),
        patch("ai.notebooklm.client.asyncio.create_subprocess_exec", return_value=proc),
    ):
        with pytest.raises(NotebookLMError, match="not valid JSON"):
            await client.index_document(notebooklm_notebook_id="nb-1", file_path="/tmp/notes.pdf")


@pytest.mark.parametrize(
    "stdout",
    [
        b'{"error": "quota exceeded"}',
        b'{"status": "error"}',
    ],
)
async def test_json_error_shaped_response_raises(stdout: bytes) -> None:
    client = NotebookLMClient()
    proc = _mock_proc(returncode=0, stdout=stdout)

    with (
        patch("ai.notebooklm.client.shutil.which", return_value="/usr/bin/nlm"),
        patch("ai.notebooklm.client.asyncio.create_subprocess_exec", return_value=proc),
    ):
        with pytest.raises(NotebookLMError, match="reported failure"):
            await client.index_document(notebooklm_notebook_id="nb-1", file_path="/tmp/notes.pdf")
