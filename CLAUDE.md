# CLAUDE.md

Instructions Claude Code needs in **every** session. Keep this file short — deep detail lives in `docs/` and `.claude/rules/`, linked below.

## Project Overview

AI Tutor: turns any learning material (PDF/DOCX/PPTX/images/URLs) into personalized study resources (notes, flashcards, quizzes, study guides) and adapts to the student over time via long-term memory and knowledge retrieval.

Full vision: `docs/PROJECT_PLAN.md`. Architecture: `docs/ARCHITECTURE.md`. Roadmap: `docs/ROADMAP.md`.

## Philosophy

- Grounded over generic: every answer/material should trace back to the student's uploaded sources when possible (RAG, citations) — not generic LLM knowledge.
- Cheap model for cheap work: route formatting/preprocessing to DeepSeek/Qwen, teaching/reasoning to Gemini, document understanding to NotebookLM. See `docs/AI.md`.
- Ship incrementally per `docs/ROADMAP.md` phases — don't build Phase 4 (RAG/memory) plumbing while Phase 1 (auth/upload) is unfinished.

## Tech Stack (summary)

Frontend: React + Vite + TypeScript, Tailwind, shadcn/ui, React Router, TanStack Query, Framer Motion, React Hook Form.
Backend: FastAPI + Python, SQLAlchemy, Celery + Redis, JWT auth.
Data: PostgreSQL (Supabase) + pgvector, Supabase Storage.
AI: Gemini 3.5 Flash (primary tutor), OpenRouter/DeepSeek/Qwen (fallback + cheap tasks), NotebookLM (knowledge engine), Tavily/Brave (search).
Deploy: Oracle Cloud VPS, Docker, Nginx, GitHub Actions.

Full detail: `docs/TECH_STACK.md`.

## Coding Standards & Conventions

- Python: `snake_case` for functions/variables, `PascalCase` for classes, type hints required on public functions, format with `ruff format`, lint with `ruff check`.
- TypeScript/React: `camelCase` for variables/functions, `PascalCase` for components/types, one component per file, functional components + hooks only (no class components).
- Files: `kebab-case` for non-component files, `PascalCase.tsx` for React components.
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Detail: `docs/WORKFLOW.md`.
- No speculative abstractions — solve the requested problem, match existing patterns, touch only relevant files (see global response-style rules already in effect for this session).
- Domain vocabulary (Notebook vs Document vs Source vs Chunk, etc.) must match `docs/GLOSSARY.md` — don't invent synonyms.

Domain-specific detail lives in `.claude/rules/`: `backend.md`, `frontend.md`, `database.md`, `ai.md`, `security.md`, `testing.md`, `ui.md`, `documentation.md`, `performance.md`, `git.md`.

## Project-Wide Rules

- Never commit secrets/API keys — use `.env` (gitignored), reference `docs/SECURITY.md`.
- Every new AI call must go through the orchestration layer (`docs/AI.md`) — no ad-hoc direct model calls from feature code.
- Every schema change ships as a migration (`.claude/rules/database.md`) — never hand-edit the DB.
- Every new architectural or dependency decision of consequence gets an ADR in `docs/adr/` (see `docs/DECISIONS.md`).
- Update `CHANGELOG.md` for user-facing changes; update the relevant `docs/*.md` in the same PR as the code it describes.

## Delegation

- Keep the main thread free: delegate investigation to the `Explore` subagent or `codex:rescue`, and implementation to the domain subagents (`backend`, `frontend`, `database`, `ai`, `tester`, `documentation`) rather than doing multi-file work inline.
- Use `codex:rescue` for a second-opinion pass on risky/high-stakes diffs (schema changes, AI prompt/schema edits, anything where a silent bug reaches production) before calling a task done.
- Fan out independent subagent work in parallel; sequence only where a real dependency exists (e.g. schema before the code that consumes it).

## Common Commands

| Task | Command |
|---|---|
| Backend install | `cd backend && uv sync` |
| Backend dev server | `cd backend && uv run uvicorn app.main:app --reload` |
| Backend tests | `cd backend && uv run pytest` |
| Backend lint/format | `cd backend && uv run ruff check . && uv run ruff format .` |
| DB migration (new) | `cd backend && uv run alembic revision --autogenerate -m "..."` |
| DB migration (apply) | `cd backend && uv run alembic upgrade head` |
| Frontend install | `cd frontend && pnpm install` |
| Frontend dev server | `cd frontend && pnpm dev` |
| Frontend tests | `cd frontend && pnpm test` |
| Frontend lint | `cd frontend && pnpm lint` |
| Full stack (local) | `docker compose up` |

## Where to Look

- Product/feature detail: `docs/FEATURES.md`, `docs/PROJECT_PLAN.md`
- Architecture & data flow: `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, `docs/API.md`
- AI system (routing, RAG, prompts, memory): `docs/AI.md`, `docs/AI_WORKFLOWS.md`, `docs/PROMPTS.md`, `docs/TOKEN_OPTIMIZATION.md`
- Frontend/UX: `docs/UI_UX.md`
- Security/deploy/observability: `docs/SECURITY.md`, `docs/DEPLOYMENT.md`, `docs/OBSERVABILITY.md`
- Testing strategy: `docs/TESTING.md`
- Why we chose X: `docs/DECISIONS.md` + `docs/adr/`
- Repo layout target: `docs/FOLDER_STRUCTURE.md`
- Contribution/branching/release process: `CONTRIBUTING.md`, `docs/WORKFLOW.md`
- Cross-agent conventions (Cursor/Codex/Gemini CLI/etc.): `AGENTS.md`
