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


@dataclass(frozen=True)
class QuerySourceCitation:
    """One `references[]` entry from a `notebook query` response."""

    notebooklm_source_id: str
    citation_number: int | None


@dataclass(frozen=True)
class NotebookQueryResult:
    """Result of asking a question against a notebook's already-indexed sources."""

    answer: str
    citations: list[QuerySourceCitation]


@dataclass(frozen=True)
class StudioArtifactCreateResult:
    """Result of kicking off one Studio artifact generation.

    Every type except `mindmap` is async: `status` comes back `"unknown"` and the caller
    must poll `get_studio_artifact_status` (live-tested 2026-08-10: `report` settled in
    ~6s, `infographic` in ~90s — `audio`/`slides`/`data_table` untested but expected
    slower, especially `audio`). `mindmap` is the one exception: `nlm mindmap create`
    returns the finished result inline (`mind_map_json` populated, `status="completed"`)
    with nothing to poll or download.
    """

    notebooklm_artifact_id: str
    status: str
    mind_map_json: str | None = None


# Lumora's own `MaterialArtifactType` values -> the CLI's `create`-group command name.
# One-to-one except `data_table`, which needs a hyphen the enum value doesn't have.
_STUDIO_CREATE_COMMAND: dict[str, str] = {
    "audio": "audio",
    "report": "report",
    "slides": "slides",
    "infographic": "infographic",
    "mindmap": "mindmap",
    "data_table": "data-table",
}

# -> the CLI's `download`-group command name. Confirmed live (2026-08-10) that this
# differs from the create-group name for `slides` ("slide-deck") and `mindmap`
# ("mind-map", per `nlm --ai`'s reference -- not live-tested since mindmap never needs
# downloading, its result is already inline from `create`).
_STUDIO_DOWNLOAD_COMMAND: dict[str, str] = {
    "audio": "audio",
    "report": "report",
    "slides": "slide-deck",
    "infographic": "infographic",
    "mindmap": "mind-map",
    "data_table": "data-table",
}


class NotebookLMClient:
    """Thin async wrapper around the `nlm` CLI for notebook/source management."""

    async def ensure_remote_notebook(
        self, *, notebooklm_notebook_id: str | None, name: str
    ) -> str:
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
        return DocumentIndexResult(
            notebooklm_source_id=source_id, status=_extract_status(payload)
        )

    async def query_notebook(
        self, *, notebooklm_notebook_id: str, question: str
    ) -> NotebookQueryResult:
        """Ask a question against a notebook's already-indexed sources and return the answer.

        Runs `nlm notebook query <notebooklm_notebook_id> <question> --json`. Confirmed
        response shape (live-tested, unlike `notebook create`/`source add` above which are
        still best-effort): `{"answer": str, "references": [{"source_id": str,
        "citation_number": int}, ...], ...}`. Missing `answer` is treated as a malformed
        response (`nlm` only returns 0/no-error-JSON once it has a real answer to give).
        """
        stdout = await _run_nlm(
            "notebook", "query", notebooklm_notebook_id, question, "--json"
        )
        payload = _parse_json(
            stdout, context=f"nlm notebook query {notebooklm_notebook_id!r}"
        )

        answer = payload.get("answer")
        if not isinstance(answer, str) or not answer:
            raise NotebookLMError(
                f"nlm notebook query {notebooklm_notebook_id!r} exited 0 with --json but no "
                f"answer was found in its output: {stdout!r}"
            )

        citations = [
            QuerySourceCitation(
                notebooklm_source_id=reference["source_id"],
                citation_number=reference.get("citation_number"),
            )
            for reference in payload.get("references", [])
            if isinstance(reference, dict)
            and isinstance(reference.get("source_id"), str)
        ]
        return NotebookQueryResult(answer=answer, citations=citations)

    async def create_studio_artifact(
        self,
        *,
        notebooklm_notebook_id: str,
        artifact_type: str,
        options: dict[str, str | int],
    ) -> StudioArtifactCreateResult:
        """Kick off generating one Studio artifact (audio/report/slides/infographic/
        mindmap/data_table) from a notebook's indexed sources.

        `artifact_type` must be a `MaterialArtifactType` value (this module doesn't import
        backend models, so it takes the plain string). `options` becomes `--key value`
        flags (underscores in keys become hyphens, e.g. `{"orientation": "portrait"}` ->
        `--orientation portrait`) -- which keys are meaningful is a per-type contract
        `nlm --ai` documents (e.g. audio: format/length/focus/language; infographic:
        orientation/detail); this method doesn't validate them, the caller (backend schema
        layer) does. `data_table` is the one exception: it needs `options["description"]`
        as a required *positional* argument, not a flag (`nlm data-table create <nb>
        "<description>" --confirm`), enforced here since silently dropping it would be a
        confusing 100%-of-the-time failure for that type.

        Every type runs `nlm <command> create <notebooklm_notebook_id> [flags] --confirm
        --json`. `mindmap` returns its full result inline (see
        `StudioArtifactCreateResult`); every other type returns `status: "unknown"` and
        must be polled via `get_studio_artifact_status`.
        """
        command = _STUDIO_CREATE_COMMAND.get(artifact_type)
        if command is None:
            raise NotebookLMError(f"Unknown Studio artifact_type: {artifact_type!r}")

        args = [command, "create", notebooklm_notebook_id]
        if artifact_type == "data_table":
            description = options.get("description")
            if not description:
                raise NotebookLMError(
                    "data_table artifacts require options['description']."
                )
            args.append(str(description))
        for key, value in options.items():
            if artifact_type == "data_table" and key == "description":
                continue
            args.extend([f"--{key.replace('_', '-')}", str(value)])
        args.extend(["--confirm", "--json"])

        stdout = await _run_nlm(*args)
        payload = _parse_json(
            stdout, context=f"nlm {command} create {notebooklm_notebook_id!r}"
        )
        artifact_id = _extract_id(payload, keys=("artifact_id", "id"))
        if artifact_id is None:
            raise NotebookLMError(
                f"nlm {command} create {notebooklm_notebook_id!r} exited 0 with --json but "
                f"no artifact id was found in its output: {stdout!r}"
            )

        mind_map_json = payload.get("mind_map_json")
        mind_map_json = mind_map_json if isinstance(mind_map_json, str) else None
        status = payload.get("status")
        if not isinstance(status, str) or not status:
            # mindmap's response has no "status" key at all (docstring above) -- its
            # presence in the payload is itself the completion signal.
            status = "completed" if mind_map_json is not None else "unknown"

        return StudioArtifactCreateResult(
            notebooklm_artifact_id=artifact_id,
            status=status,
            mind_map_json=mind_map_json,
        )

    async def get_studio_artifact_status(
        self, *, notebooklm_notebook_id: str, artifact_id: str
    ) -> str:
        """Poll one artifact's generation status.

        Runs `nlm studio status <notebooklm_notebook_id> --json`, which -- unlike every
        other `--json` call in this module -- returns a JSON *array* of every artifact in
        the notebook (confirmed live 2026-08-10: `[{"id", "artifact_id", "type",
        "status", ...}, ...]`), not a single object. Returns that artifact's `status`
        string (e.g. `"unknown"`, `"completed"`, `"failed"`).
        """
        stdout = await _run_nlm("studio", "status", notebooklm_notebook_id, "--json")
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise NotebookLMError(
                f"nlm studio status {notebooklm_notebook_id!r}: exited 0 but stdout was not "
                f"valid JSON: {stdout!r}"
            ) from exc
        if not isinstance(payload, list):
            raise NotebookLMError(
                f"nlm studio status {notebooklm_notebook_id!r}: expected a JSON array, got: "
                f"{stdout!r}"
            )

        for entry in payload:
            if isinstance(entry, dict) and entry.get("artifact_id") == artifact_id:
                status = entry.get("status")
                return status if isinstance(status, str) and status else "unknown"

        raise NotebookLMError(
            f"nlm studio status {notebooklm_notebook_id!r}: artifact {artifact_id!r} not "
            f"found in the status list: {stdout!r}"
        )

    async def download_studio_artifact(
        self,
        *,
        notebooklm_notebook_id: str,
        artifact_type: str,
        artifact_id: str,
        output_path: str,
    ) -> None:
        """Download a completed artifact's file to `output_path` on local disk.

        Runs `nlm download <command> <notebooklm_notebook_id> --id <artifact_id> --output
        <output_path>`. Only call this once `get_studio_artifact_status` has returned
        `"completed"` -- `mindmap` never needs this (its result is already inline from
        `create_studio_artifact`). Like `index_document`, this doesn't manage
        `output_path` itself: the caller creates and later cleans up the temp file.
        """
        command = _STUDIO_DOWNLOAD_COMMAND.get(artifact_type)
        if command is None:
            raise NotebookLMError(f"Unknown Studio artifact_type: {artifact_type!r}")

        await _run_nlm(
            "download",
            command,
            notebooklm_notebook_id,
            "--id",
            artifact_id,
            "--output",
            output_path,
        )


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
        raise NotebookLMError(
            f"{context}: nlm reported failure in its JSON output: {stdout!r}"
        )

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
