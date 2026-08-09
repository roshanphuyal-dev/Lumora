# Folder Structure

## Purpose

The authoritative target repo layout — including modules that don't exist yet. When creating a new top-level directory or restructuring an existing one, this doc is updated first (or in the same PR), so it never drifts from reality for long.

## What Belongs Here

- The full intended directory tree, annotated.
- Rationale for non-obvious placement decisions.

## What Never Belongs Here

- Coding conventions within a folder (`.claude/rules/*.md`).
- Feature-to-file mapping (too granular; discoverable via search/`docs/ARCHITECTURE.md`).

## Structure

### Current (scaffolded)

```
ai-tutor/
├── CLAUDE.md
├── README.md
├── AGENTS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── .gitignore
├── docs/
├── .claude/
├── frontend/    (stub — see frontend/README.md)
├── backend/     (auth, courses/subjects, documents, notebooks scaffolded — see below)
├── database/    (stub — see database/README.md)
├── ai/          (orchestrator, Gemini + NotebookLM clients scaffolded — see below)
├── tests/       (stub — see tests/README.md)
└── docker/      (docker-compose.yml — local Postgres + Redis)
```

`backend/` current contents (Milestone 1 — auth, users, courses/subjects; Milestone 2 — documents, notebooks, parsing, Celery):
```
backend/
├── app/
│   ├── api/v1/       # auth.py, users.py, courses.py, documents.py, notebooks.py
│   ├── core/         # config.py, security.py, dependencies.py, storage.py (FileStorage seam)
│   ├── db/           # session.py (async engine/session, Base)
│   ├── models/       # base.py, user.py, course.py, document.py, notebook.py
│   ├── schemas/      # auth.py, user.py, course.py, document.py, notebook.py
│   ├── services/     # auth_service.py, user_service.py, course_service.py, document_service.py, notebook_service.py
│   ├── parsers/      # base.py, registry.py, pdf/pptx/docx/image_parser.py
│   ├── rag/          # empty — Milestone 3
│   ├── workers/      # celery_app.py, document_tasks.py, notebook_tasks.py
│   └── main.py
├── alembic/           # env.py + versions/ (users/courses/subjects; documents/notebooks/notebook_sources)
├── scripts/           # seed_test_user.py — one-off/maintenance scripts (docs/FOLDER_STRUCTURE.md's "added when the first one is needed" — this is it)
├── tests/             # conftest.py, test_auth.py, test_courses.py, test_document_service.py, test_document_tasks.py, test_parsers.py, test_storage.py
├── .env.example
└── pyproject.toml
```

`ai/` current contents (Milestone 2 — orchestrator + first two provider clients, `docs/AI.md#routing-logic`):
```
ai/
├── orchestrator/      # task_types.py (TaskType enum), schemas.py, orchestrator.py (run_task)
├── gemini/            # client.py — real google-genai call (Gemini 2.5 Flash)
├── notebooklm/        # client.py — typed interface, CLI/MCP call still stubbed (always raises)
└── prompts/           # teaching_explanation_v1.py
```

### Target (as modules are implemented)

```
backend/
├── app/
│   ├── api/            # FastAPI routers, one module per API group (docs/API.md)
│   ├── core/           # config, security, dependencies
│   ├── models/          # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # business logic
│   ├── parsers/          # PDF/DOCX/PPTX/OCR extraction
│   ├── rag/              # chunking, retrieval, context assembly
│   ├── workers/           # Celery tasks
│   └── main.py
├── alembic/              # migrations
└── tests/

ai/
├── orchestrator/         # routing/task-type dispatch (docs/AI.md)
├── gemini/               # Gemini client + prompt invocation
├── notebooklm/            # NotebookLM CLI/MCP integration
├── openrouter/             # DeepSeek/Qwen fallback client
├── prompts/                # prompt templates (docs/PROMPTS.md)
├── embeddings/              # embedding generation
├── routing/                  # task_type → provider decision logic
└── cache/                     # prompt/response cache layer

frontend/
├── src/
│   ├── components/       # shadcn-based + custom components
│   ├── pages/             # route-level components
│   ├── hooks/              # custom hooks (TanStack Query wrappers, etc.)
│   ├── lib/                  # utilities, API client
│   └── routes/                # React Router config
└── public/

database/
├── migrations/            # if not colocated with backend/alembic
└── seed/                    # seed data scripts

tests/
└── e2e/                    # cross-cutting Playwright suites

docker/
├── backend.Dockerfile
├── frontend.Dockerfile
└── docker-compose.yml
```

### Not Yet Created (documented here, not scaffolded)
- `.github/workflows/` — CI/CD pipelines (`docs/DEPLOYMENT.md`), added when Phase 1 nears deployment.
- `scripts/` — one-off/maintenance scripts, added when the first one is actually needed.

Rationale: empty directories aren't tracked by git and add no value before there's content to put in them — see `docs/adr/` if this default is ever revisited.

<!-- TODO: update this tree as each module is actually scaffolded; treat drift here as a bug -->
