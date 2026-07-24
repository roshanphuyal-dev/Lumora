"""NotebookLM provider client (ADR 0004).

The only place NotebookLM CLI calls should be made (.claude/rules/ai.md). There is no
public NotebookLM REST API (ADR 0004), so this shells out to the `nlm` CLI from
`notebooklm-mcp-cli` (https://github.com/jacob-bd/notebooklm-mcp-cli, installed via
`uv tool install notebooklm-mcp-cli`) as an async subprocess. `nlm` is not a Python
library — there is no `import` interface, only the CLI binary.

Auth is cookie-based and out-of-band: a human runs `nlm login` once per machine (it opens
a browser). This module never attempts to log in itself — it assumes a profile may or may
not be authenticated yet, and surfaces `nlm`'s own failure output (which names the auth
problem) rather than guessing at what went wrong.

This module has no DB access (`.claude/rules/ai.md` — `ai/` is provider-integration code
only). `ensure_remote_notebook` and `index_document` both return data for the caller to
persist; neither writes to Lumora's database.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass

_NLM_BINARY = "nlm"
_INSTALL_HINT = "install via `uv tool install notebooklm-mcp-cli`"
_LOGIN_HINT = "run `nlm login` once on this machine to authenticate"


class NotebookLMError(RuntimeError):
    """Raised when the `nlm` CLI is missing, its call fails, or its output is unusable."""


@dataclass(frozen=True)
class DocumentIndexResult:
    """Result of indexing one document as a NotebookLM source."""

    notebooklm_source_id: str
    status: str  # "indexed" | "failed"


class NotebookLMClient:
    """Thin async wrapper around the `nlm` CLI for notebook/source management."""

    async def ensure_remote_notebook(self, *, notebooklm_notebook_id: str | None, name: str) -> str:
        """Return a remote NotebookLM notebook id, creating one via `nlm` if needed.

        If `notebooklm_notebook_id` is already set (i.e. a `Notebook` row already has a
        remote counterpart), it is returned as-is and no CLI call is made. Otherwise this
        runs `nlm notebook create "<name>" --json`, parses the response, and returns the
        newly created notebook's id.

        Callers pass in `notebook.notebooklm_notebook_id` and `notebook.name` rather than
        a `Notebook` ORM instance — this module doesn't import backend models (`ai/` isn't
        DB-aware and shouldn't depend on `backend/app/models`, per the same isolation rule
        that keeps provider SDKs out of `backend/`). This function does NOT persist a
        newly created id back to the `notebooks` table; when the returned id differs from
        the `notebooklm_notebook_id` passed in, the caller is responsible for saving it
        (see `ai/README.md` / this repo's AI docs for which service layer owns that write).
        """
        if notebooklm_notebook_id:
            return notebooklm_notebook_id

        stdout = await _run_nlm("notebook", "create", name, "--json")
        payload = _parse_json(stdout, context=f"nlm notebook create {name!r}")
        remote_id = _extract_id(payload, keys=("id", "notebook_id", "notebookId"))
        if remote_id is None:
            raise NotebookLMError(
                f"nlm notebook create {name!r} exited 0 with --json but no notebook id "
                f"was found in its output: {stdout!r}"
            )
        return remote_id

    async def index_document(
        self, *, notebooklm_notebook_id: str, file_path: str
    ) -> DocumentIndexResult:
        """Upload and index one local file as a NotebookLM source, waiting for completion.

        `file_path` MUST be a path to a file that already exists on local disk — the `nlm`
        CLI uploads via `--file <path>`; it has no stdin/bytes-payload mode. If the caller
        only has document bytes (e.g. via `app/core/storage.py`'s `FileStorage.download`),
        it must first write them to a temp file (`tempfile.NamedTemporaryFile` or similar)
        and pass that path here — this client does not manage temp files itself, and does
        not delete `file_path` afterwards.

        Runs `nlm source add <notebooklm_notebook_id> --file <file_path> --wait --json`.
        `--wait` blocks the subprocess until NotebookLM finishes indexing server-side
        (this coroutine awaits that, it doesn't block the event loop) — without it the
        call would return before indexing completes and the returned status would be
        meaningless.
        """
        stdout = await _run_nlm(
            "source",
            "add",
            notebooklm_notebook_id,
            "--file",
            file_path,
            "--wait",
            "--json",
        )
        payload = _parse_json(stdout, context=f"nlm source add --file {file_path!r}")
        source_id = _extract_id(payload, keys=("id", "source_id", "sourceId"))
        if source_id is None:
            raise NotebookLMError(
                f"nlm source add --file {file_path!r} exited 0 with --json but no source "
                f"id was found in its output: {stdout!r}"
            )
        return DocumentIndexResult(notebooklm_source_id=source_id, status=_extract_status(payload))


async def _run_nlm(*args: str) -> str:
    """Run `nlm <args>` as an async subprocess and return its stdout on success.

    Raises `NotebookLMError` for every failure mode, with enough detail to actually debug
    it instead of a generic wrapper message:
      - `nlm` not on PATH -> distinct, actionable "not installed" message.
      - non-zero exit code -> includes `nlm`'s real stderr/stdout (this is how an auth
        failure from a not-yet-`nlm login`'d profile surfaces).
    """
    if shutil.which(_NLM_BINARY) is None:
        raise NotebookLMError(f"nlm CLI not found on PATH — {_INSTALL_HINT}.")

    try:
        proc = await asyncio.create_subprocess_exec(
            _NLM_BINARY,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
    except FileNotFoundError as exc:
        # Belt-and-suspenders: shutil.which() and exec can race, or a stale PATH entry
        # can point at something that isn't actually executable. Keep this distinct from
        # the generic non-zero-exit path below per the same "actionable, not generic" bar.
        raise NotebookLMError(f"nlm CLI not found — {_INSTALL_HINT}.") from exc

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        raise NotebookLMError(
            f"nlm {' '.join(args)} failed (exit code {proc.returncode}).\n"
            f"stderr: {stderr or '<empty>'}\n"
            f"stdout: {stdout or '<empty>'}\n"
            f"If this is an authentication error, {_LOGIN_HINT}."
        )

    return stdout


def _parse_json(stdout: str, *, context: str) -> dict:
    """Parse `nlm --json` stdout, raising `NotebookLMError` with the raw output on failure.

    Covers both "not JSON at all" and "valid JSON but shaped like an error" — `nlm`'s
    exact error-JSON schema isn't pinned down in its docs, so this checks the plausible
    conventions (`error` key present, or `status: "error"`) rather than assuming one.
    """
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise NotebookLMError(
            f"{context}: nlm exited 0 but stdout was not valid JSON: {stdout!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise NotebookLMError(
            f"{context}: nlm --json output was valid JSON but not an object: {stdout!r}"
        )

    if payload.get("error") or payload.get("status") == "error":
        raise NotebookLMError(f"{context}: nlm reported failure in its JSON output: {stdout!r}")

    return payload


def _extract_id(payload: dict, *, keys: tuple[str, ...]) -> str | None:
    """Best-effort id extraction across `nlm`'s plausible JSON key/nesting conventions.

    `notebooklm-mcp-cli`'s exact `--json` response shape for `notebook create`/`source
    add` isn't documented with a full field reference at the time of writing (only that
    ids come back as JSON, e.g. `notebooks[0]["id"]` for `notebook list`). This tries the
    given top-level key names, then the same keys one level down under common wrapper
    keys, instead of hard-coding a single assumed shape.
    """
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    for nested_key in ("notebook", "source", "data", "result"):
        nested = payload.get(nested_key)
        if isinstance(nested, dict):
            nested_id = _extract_id(nested, keys=keys)
            if nested_id is not None:
                return nested_id

    return None


def _extract_status(payload: dict) -> str:
    """Return the indexing status from a `source add` response, defaulting to "indexed".

    `--wait` only returns after `nlm` reports the source ready (a non-zero exit / error
    JSON is caught before this is called), so the absence of an explicit `status` field is
    treated as success rather than left unset.
    """
    status = payload.get("status")
    if isinstance(status, str) and status:
        return status
    return "indexed"
