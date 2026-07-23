# AI Tutor

Production-quality AI-powered personal tutor. Turns any learning material — PDFs, slides, documents, images, URLs — into personalized study resources, and adapts to each student's strengths and weaknesses over time through long-term memory, retrieval-augmented grounding, and intelligent tutoring.

> Status: early development (Phase 1 — see [Roadmap](#roadmap)).

## Screenshots

| Dashboard | Notebook / Sources | Quiz Engine |
|---|---|---|
| _placeholder_ | _placeholder_ | _placeholder_ |

## Features

- **Document ingestion** — PDF, DOCX, PPTX, images (OCR), URLs
- **Notebook knowledge base** — multi-document notebooks with citation-grounded retrieval (NotebookLM-backed)
- **Study material generation** — notes, study guides, mind maps, flashcards, cheat sheets, timelines, comparison tables, slides, audio summaries
- **Quiz generation & engine** — MCQ, true/false, fill-in-blank, matching, short/long answer, case studies, adaptive difficulty
- **AI evaluation** — scoring, mistake analysis, personalized feedback, weak-topic detection
- **AI chat tutor** — Socratic teaching, follow-ups, multi-document comparison, source citation
- **Internet research** — current info, papers, images, fact verification (Tavily/Brave)
- **Overleaf/LaTeX export** — notes, assignments, reports, formula sheets
- **Progress tracking & analytics** — mastery, streaks, heatmaps, improvement trends

Full feature catalogue: [`docs/FEATURES.md`](docs/FEATURES.md). Full product vision: [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md).

## Tech Stack

Frontend (React/Vite/TS/Tailwind/shadcn) · Backend (FastAPI/Python/Celery) · PostgreSQL+pgvector (Supabase) · Gemini + NotebookLM + OpenRouter AI layer · Oracle Cloud/Docker/Nginx deployment.

Details: [`docs/TECH_STACK.md`](docs/TECH_STACK.md). Decision rationale: [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Installation

Prerequisites: Python 3.12+, [`uv`](https://github.com/astral-sh/uv), Node 20+, [`pnpm`](https://pnpm.io), Docker, a PostgreSQL instance (or Supabase project) with `pgvector` enabled.

```bash
git clone <repo-url> ai-tutor && cd ai-tutor

# Backend
cd backend
uv sync
cp .env.example .env   # fill in DB, Gemini, NotebookLM, search API keys
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
pnpm install
cp .env.example .env
pnpm dev

# Or: full stack via Docker
docker compose up
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for local dev workflow and [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for production setup.

## Project Structure

```
ai-tutor/
├── CLAUDE.md            # Claude Code session context
├── AGENTS.md             # cross-agent (Cursor/Codex/etc.) conventions
├── docs/                 # architecture, AI system, database, API, decisions...
├── .claude/              # rules, skills, agents, commands for Claude Code
├── frontend/             # React + Vite + TS
├── backend/              # FastAPI + Python
├── database/             # migrations, seed data
├── ai/                   # orchestration, prompts, RAG, embeddings
├── tests/                # cross-cutting/e2e tests
└── docker/               # Dockerfiles, compose
```

Full target layout: [`docs/FOLDER_STRUCTURE.md`](docs/FOLDER_STRUCTURE.md).

## Development Workflow

Trunk-based: short-lived feature branches off `main`, PR + review, squash-merge. Conventional Commits. See [`docs/WORKFLOW.md`](docs/WORKFLOW.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Roadmap

1. **Phase 1** — Auth, dashboard, upload/parsing, NotebookLM + Gemini integration
2. **Phase 2** — Notes, flashcards, study guides, AI chat, knowledge base
3. **Phase 3** — Quiz generation/engine, AI evaluation, internet search, images
4. **Phase 4** — RAG, memory, personalized/adaptive tutoring, citations
5. **Phase 5** — Voice tutor, whiteboard, mobile app, AI agents, advanced analytics

Full roadmap with milestones: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, branching, commit conventions, and review expectations. AI coding agents should also read [`AGENTS.md`](AGENTS.md).

## License

TBD.
