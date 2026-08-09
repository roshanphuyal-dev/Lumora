# AI System Handbook

## Purpose

The central reference for how AI actually works in this product: orchestration, models, RAG, embeddings, memory, personalization, cost. This is the doc meant to grow into the full AI handbook — when in doubt about *how AI decisions get made*, it belongs here.

## What Belongs Here

- Orchestration/routing logic (which provider handles what, and why).
- Model roster and their assigned responsibilities.
- RAG design: chunking, embeddings, retrieval, context assembly.
- Memory and personalization design.
- Vector DB usage patterns.

## What Never Belongs Here

- Step-by-step feature pipelines (upload → notes, question → answer) — those go in `docs/AI_WORKFLOWS.md`, which references this doc for the *why*.
- Actual prompt text/templates — those go in `docs/PROMPTS.md`.
- Cost-reduction tactics in detail — those go in `docs/TOKEN_OPTIMIZATION.md` (this doc explains *what* routes where; that doc explains *how to make routing cheap*).
- Endpoint contracts — `docs/API.md`.

## Structure

### AI Architecture

```
FastAPI Backend → AI Orchestration Layer → { NotebookLM | Gemini | DeepSeek/Qwen } → Response
                                                    │
                                    Internet Search + Image Retrieval (as needed)
                                                    │
                                    PostgreSQL + pgvector (context, memory, cache)
```

The orchestration layer (`ai/orchestrator/`) is the *only* place feature code talks to a model provider. It receives a task type + context, returns a normalized response. Feature code never imports a provider SDK directly — see `.claude/rules/ai.md`.

### Model Roster & Responsibilities

| Model | Responsibility |
|---|---|
| **Gemini 2.5 Flash** (primary) | Teaching, personalized explanations, quiz generation/grading, feedback, LaTeX generation, study planning, adaptive tutoring |
| **NotebookLM** (knowledge engine) | Document indexing, long-context understanding, multi-document reasoning, citation retrieval, study guide/mind map/flashcard/audio generation, report generation |
| **DeepSeek / Qwen** (via OpenRouter, cheap tier) | Formatting, basic summaries, markdown/JSON generation, cheap preprocessing |
| **OpenCode Zen** (free-tier fallback) | Fallback for teaching/explanation tasks when Gemini is unavailable, rate-limited, or its daily quota is exhausted (ADR 0008) |
| **OpenRouter** | Cheap-tier routing (DeepSeek/Qwen, step 3 below) — not yet wired as a Gemini fallback; OpenCode Zen fills that role instead (ADR 0008) |

### Routing Logic (decision order)

1. **Is this a document-grounded question or does it need multi-doc reasoning/citations?** → NotebookLM first, then hand its output to Gemini for teaching framing if needed.
2. **Is this teaching, explanation, grading, or anything requiring pedagogical judgment?** → Gemini.
3. **Is this pure formatting, reformatting, or cheap transformation (e.g. "turn this into a markdown table")?** → DeepSeek/Qwen via OpenRouter.
4. **Is this current-events/external-fact-dependent?** → Search (Tavily/Brave) first, then Gemini to synthesize.
5. **Gemini unavailable, rate-limited, or its daily quota exhausted?** → OpenCode Zen fallback (free-tier model, `ai/opencode_zen/client.py`), and vice versa (OpenCode Zen failing falls back to Gemini) — ADR 0008. A degraded-quality flag is not yet surfaced to the caller; `AIResponse.provider` (`ai/orchestrator/schemas.py`) tells the caller which one actually answered.

Routing decisions are made once, at the orchestration layer, based on a `task_type` enum — feature code declares *what it needs*, not *which model to call*.

**Implementation status (Phase 1):** the `task_type` enum lives in `ai/orchestrator/task_types.py`; routing is implemented in `ai/orchestrator/orchestrator.py`. Routing-order steps 1, 2, and 5 above exist so far — `DOCUMENT_INDEX` and `NOTEBOOK_QUERY` → NotebookLM, `TEACHING_EXPLANATION` → Gemini falling back to OpenCode Zen; search-first routing and the OpenRouter cheap tier (steps 3–4) aren't built yet. The Gemini call is real (`ai/gemini/client.py`, `google-genai`, Gemini 2.5 Flash). The OpenCode Zen call is real too (`ai/opencode_zen/client.py`, OpenAI-compatible HTTP API, `deepseek-v4-flash-free` model) but unverified against a live authenticated key at the time this was written — see `docs/DECISIONS.md#known-debt-not-yet-adr-worthy`. The NotebookLM call is also real now — `ai/notebooklm/client.py` shells out to the `nlm` CLI (`notebooklm-mcp-cli`) as an async subprocess: `ensure_remote_notebook` creates/reuses the notebook's remote NotebookLM id (cached on `Notebook.notebooklm_notebook_id`), `index_document` uploads the source file and blocks (`--wait`) until NotebookLM finishes indexing server-side, and `query_notebook` asks a question against a notebook's already-indexed sources (`nlm notebook query <id> <question> --json`), returning an answer plus source citations. Auth is out-of-band (`nlm login`, once per machine — `docs/DEPLOYMENT.md#manual-deploy-prerequisites-not-automatable-via-envsecrets`), not an env var. `index_document`/`ensure_remote_notebook` and `query_notebook` have now been live-smoke-tested against an authenticated `nlm` profile — `notebook create`/`source add`'s exact `--json` shape is still only best-effort-matched (`_extract_id`'s defensive key search), but `notebook query`'s response shape (`{"answer", "references": [{"source_id", "citation_number"}], ...}`) is confirmed, not guessed.

`ask_question` (`app/services/notebook_service.py`) uses `NOTEBOOK_QUERY` to ground a student's question before handing it to Gemini as `context` for teaching framing (`docs/AI_WORKFLOWS.md#4`) whenever the notebook has at least one `indexed` source; a notebook with no indexed sources, or a failed NotebookLM call, falls back to the previous ungrounded Gemini-only call rather than failing the request.

### RAG Design

- **Chunking**: documents split into semantically coherent chunks (target size TBD in implementation) at ingest time, not at query time.
- **Embeddings**: Gemini Embeddings (primary) or Jina Embeddings (fallback/comparison), stored in `pgvector`.
- **Retrieval**: top-k similarity search scoped to the active notebook's sources, re-ranked before being handed to Gemini as context.
- **Context assembly**: retrieved chunks + citation metadata + conversation history (compressed, see `docs/TOKEN_OPTIMIZATION.md`) assembled into the prompt via `docs/PROMPTS.md` templates.
- **Source grounding**: every generated answer that draws on a notebook should carry citation metadata back to the originating chunk/source.

### Memory & Personalization

- **Short-term**: conversation history within a session/chat, compressed before reuse.
- **Long-term**: per-student weak-topic history, quiz performance, mastery levels — persisted in Postgres (`docs/DATABASE.md`), fed back into prompt context for adaptive tutoring and study planning.
- **Personalization inputs**: weak topics, past mistakes, preferred explanation depth/style, revision history.

### Model Selection Heuristics
Small/cheap model → formatting. Medium → summaries. NotebookLM → document understanding. Gemini → complex reasoning/teaching. Selection is automatic (orchestration layer), never hardcoded per-feature.

<!-- TODO: document actual chunk size/overlap once tuned against real documents -->
<!-- TODO: document re-ranking algorithm once selected -->
