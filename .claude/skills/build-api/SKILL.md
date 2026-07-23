---
name: build-api
description: Build a new FastAPI endpoint/API group following this repo's conventions. Use when asked to add a new API endpoint or endpoint group.
---

# Build API

## Objective
Add a new FastAPI endpoint (or group) consistent with `docs/API.md` conventions and `.claude/rules/backend.md`.

## Inputs
- Endpoint purpose, HTTP method, request/response shape.
- Which existing API group it belongs to (`docs/API.md#endpoint-groups`), or justification for a new one.

## Outputs
- Router function with Pydantic request/response schemas.
- Service-layer function containing the actual logic (not inline in the route handler).
- Tests covering the endpoint (`docs/TESTING.md`).
- `docs/API.md` updated if a new endpoint group or convention-affecting endpoint was added.

## Expected Quality
- Follows `/api/v1/` prefix and standard error shape (`docs/API.md#conventions`).
- Auth/authorization applied via dependency injection, scoped to the authenticated user's own data.
- Async, non-blocking; long-running work dispatched to Celery.

## Completion Checklist
- [ ] Route handler thin; logic in a service function.
- [ ] Pydantic schemas for request/response.
- [ ] Auth dependency applied, data scoped to authenticated user.
- [ ] Tests added.
- [ ] `docs/API.md` updated if the endpoint group changed.
