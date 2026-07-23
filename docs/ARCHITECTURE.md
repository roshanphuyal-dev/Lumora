# Architecture

## Purpose

The system-level map: how the major components (frontend, backend, AI orchestration, storage) fit together and talk to each other. The doc to read before touching a cross-cutting concern or adding a new component.

## What Belongs Here

- Component diagram and data flow.
- Service boundaries and responsibilities (what owns what).
- Cross-cutting concerns: auth flow, background job flow, caching strategy overview.
- Links to the domain-specific deep-dives (`AI.md`, `DATABASE.md`, `API.md`) rather than repeating their content.

## What Never Belongs Here

- AI routing/prompt detail (`AI.md`).
- Table-by-table schema (`DATABASE.md`).
- Endpoint-by-endpoint spec (`API.md`).
- Deployment topology detail (`DEPLOYMENT.md`) — this doc covers logical architecture, not infra.

## Structure

### System Overview

```
User → Frontend (React/Vite) → FastAPI Backend → AI Orchestration Layer
                                                        │
                                    ┌───────────────────┼────────────────────┐
                                    ▼                    ▼                    ▼
                              NotebookLM             Gemini            DeepSeek/Qwen
                          (knowledge engine)     (teaching/reasoning)  (cheap formatting)
                                    │
                                    ▼
                     Internet Search + Image Retrieval (Tavily/Brave, Wikimedia/Openverse/Unsplash)
                                    │
                                    ▼
                    PostgreSQL + pgvector + Redis Cache (Supabase)
                                    │
                                    ▼
                    Personalized Learning & Analytics
```

### Component Responsibilities
- **Frontend**: presentation, client-side state (TanStack Query), form handling — no business logic, no direct AI provider calls.
- **Backend (FastAPI)**: auth, request validation, orchestration entrypoint, persistence, background job dispatch (Celery).
- **AI Orchestration Layer** (`ai/orchestrator/`): decides which provider handles a given request. Detail: `docs/AI.md`.
- **Celery + Redis**: async document processing (parsing, embedding, indexing), long-running generation jobs, caching layer.
- **PostgreSQL + pgvector**: system of record + vector similarity search for RAG.
- **Supabase Storage**: raw uploaded files (PDFs, images, etc.).

### Request Lifecycle (typical)
1. Client calls a FastAPI endpoint (`docs/API.md`).
2. Endpoint validates input, persists/reads via SQLAlchemy, and — if AI involved — calls the orchestration layer.
3. Orchestration layer routes to NotebookLM (retrieval) and/or Gemini (generation) and/or DeepSeek/Qwen (formatting), per `docs/AI.md`.
4. Long-running work (parsing, embedding, indexing, audio generation) is dispatched to Celery and polled/streamed back to the client.
5. Response persisted (cache + DB) so identical requests are served from cache — `docs/TOKEN_OPTIMIZATION.md`.

### Auth Flow
JWT-based; login/register/Google OAuth issue a token; FastAPI dependency validates on protected routes. Detail: `.claude/rules/security.md`, `docs/SECURITY.md`.

### Background Processing
Celery workers handle: document parsing/OCR, chunking + embedding generation, NotebookLM indexing, audio overview generation, scheduled analytics rollups. Redis is both the Celery broker and the response/prompt cache (`docs/TOKEN_OPTIMIZATION.md`).

<!-- TODO: add sequence diagram for "upload → notebook ready" once Phase 1 ships -->
<!-- TODO: document caching layer keys/TTLs once implemented -->
