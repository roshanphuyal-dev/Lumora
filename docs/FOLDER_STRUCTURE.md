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
├── docs/
├── .claude/
├── frontend/    (stub — see frontend/README.md)
├── backend/     (stub — see backend/README.md)
├── database/    (stub — see database/README.md)
├── ai/          (stub — see ai/README.md)
├── tests/       (stub — see tests/README.md)
└── docker/      (stub — see docker/README.md)
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
