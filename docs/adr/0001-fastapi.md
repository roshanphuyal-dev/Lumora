# ADR 0001: Why FastAPI

## Status
Accepted

## Context
Needed a Python backend framework capable of: async I/O (for calling AI providers/NotebookLM/search APIs without blocking), automatic request validation, and auto-generated API docs to keep `docs/API.md` from having to hand-maintain a full spec.

## Decision
Use FastAPI as the backend web framework.

## Alternatives Considered
- **Flask** — simpler, larger ecosystem maturity, but no native async support or built-in validation/OpenAPI generation; would need Flask-RESTX/Pydantic bolted on to match FastAPI's out-of-the-box behavior.
- **Django (+ DRF)** — batteries-included (admin, ORM), but heavier than needed for an API-first product, and its sync-first ORM/request model fights the async-heavy AI-orchestration workload here.

## Tradeoffs
Smaller ecosystem than Django/Flask for some niche integrations; async-everywhere requires discipline (blocking calls in async routes silently degrade performance) — mitigated by Celery for genuinely long-running work.

## Consequences
All I/O-bound endpoints (especially AI-routed ones) should be `async def`; SQLAlchemy usage should favor the async engine; Pydantic schemas (`docs/API.md`) double as both validation and OpenAPI doc generation, so they should stay the source of truth for request/response shape.
