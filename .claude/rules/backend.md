# Backend Rules

## Purpose
FastAPI/Python backend conventions — applies to anything under `backend/`.

## Responsibilities
Auth, request validation, persistence, background job dispatch, orchestration entrypoint (never AI provider calls directly — see `ai.md`).

## Coding Rules
- Type hints on every public function/method signature.
- `async def` for any endpoint/function doing I/O (DB, network, model calls); no blocking calls inside async functions.
- Pydantic schemas for all request/response bodies — never return raw SQLAlchemy models.
- One router per API group (`docs/API.md`), mounted under `/api/v1/`.
- Business logic lives in `services/`, not in route handlers — route handlers validate + call a service + return.

## Conventions
- `snake_case` functions/variables, `PascalCase` classes.
- Errors raised as `HTTPException` with the project's standard error shape (`docs/API.md#conventions`).
- Long-running work dispatched to Celery, never run synchronously in a request handler.

## Best Practices
- Query only what's needed (avoid `SELECT *` via ORM defaults where a subset suffices).
- Use dependency injection (FastAPI `Depends`) for auth/DB session, not module-level globals.
- Migrations via Alembic autogenerate + hand review (`docs/DATABASE.md#migration-conventions`).

## Avoid
- Direct AI provider SDK imports outside `ai/` — always go through the orchestration layer.
- Synchronous blocking I/O in async routes.
- Business logic in Pydantic schemas or route handlers.
- Manual DB schema edits outside a migration.

## Review Checklist
- [ ] Endpoint uses Pydantic request/response models.
- [ ] No blocking calls in `async def`.
- [ ] Business logic is in a service, not the route handler.
- [ ] New queries scoped to the authenticated user (no cross-user data leakage).
- [ ] Passes `ruff check` + `ruff format`.
- [ ] Has test coverage (`docs/TESTING.md`).
