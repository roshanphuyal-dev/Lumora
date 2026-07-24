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
| **OpenRouter** | Fallback routing when Gemini is unavailable/rate-limited |

### Routing Logic (decision order)

1. **Is this a document-grounded question or does it need multi-doc reasoning/citations?** → NotebookLM first, then hand its output to Gemini for teaching framing if needed.
2. **Is this teaching, explanation, grading, or anything requiring pedagogical judgment?** → Gemini.
3. **Is this pure formatting, reformatting, or cheap transformation (e.g. "turn this into a markdown table")?** → DeepSeek/Qwen via OpenRouter.
4. **Is this current-events/external-fact-dependent?** → Search (Tavily/Brave) first, then Gemini to synthesize.
5. **Gemini unavailable or rate-limited?** → OpenRouter fallback (DeepSeek/Qwen) with a degraded-quality flag surfaced to the caller.

Routing decisions are made once, at the orchestration layer, based on a `task_type` enum — feature code declares *what it needs*, not *which model to call*.

**Implementation status (Phase 1):** the `task_type` enum lives in `ai/orchestrator/task_types.py`; routing is implemented in `ai/orchestrator/orchestrator.py`. Only the first two routing-order steps above exist so far — `DOCUMENT_INDEX` → NotebookLM and `TEACHING_EXPLANATION` → Gemini; search fallback and OpenRouter degraded-quality fallback (steps 3–5) aren't built yet. The Gemini call is real (`ai/gemini/client.py`, `google-genai`, Gemini 2.5 Flash). The NotebookLM call is also real now — `ai/notebooklm/client.py` shells out to the `nlm` CLI (`notebooklm-mcp-cli`) as an async subprocess: `ensure_remote_notebook` creates/reuses the notebook's remote NotebookLM id (cached on `Notebook.notebooklm_notebook_id`), and `index_document` uploads the source file and blocks (`--wait`) until NotebookLM finishes indexing server-side. Auth is out-of-band (`nlm login`, once per machine — `docs/DEPLOYMENT.md#manual-deploy-prerequisites-not-automatable-via-envsecrets`), not an env var. This has not been exercised against a live, authenticated `nlm` profile yet (`docs/DECISIONS.md#known-debt-not-yet-adr-worthy`) — the response-parsing is defensive against a few plausible `--json` output shapes rather than a confirmed schema, so treat it as implemented-but-unverified until a live smoke test happens.

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
