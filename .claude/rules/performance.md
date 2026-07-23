# Performance Rules

## Purpose
Keep the app fast and AI spend low — applies backend, frontend, and AI orchestration.

## Responsibilities
Avoid unnecessary work (redundant queries, redundant model calls, unnecessary re-renders).

## Coding Rules
- Cache identical AI prompts/responses (`docs/TOKEN_OPTIMIZATION.md`) — check cache before calling a provider.
- Long-running work (parsing, embedding, generation) dispatched to Celery, never blocking a request.
- Frontend: avoid unnecessary re-renders (memoize expensive computations/components where profiling shows it's warranted — don't pre-optimize blindly).

## Conventions
- Batch embedding generation instead of one-at-a-time calls where the pipeline allows it.
- Paginate all list endpoints (`docs/API.md#conventions`) — never return unbounded result sets.

## Best Practices
- Send only relevant chunks (RAG) to a model, not entire documents (`docs/TOKEN_OPTIMIZATION.md#request-optimization`).
- Index every foreign key and hot-path filter/sort column (`docs/DATABASE.md#indexing-strategy`).

## Avoid
- Calling an AI provider inside a loop without batching/caching.
- N+1 queries (use eager loading where the access pattern is known).
- Premature micro-optimization without a profiling signal justifying it.

## Review Checklist
- [ ] No redundant AI calls for identical/cacheable requests.
- [ ] Long-running work goes through Celery, not the request thread.
- [ ] List endpoints paginated.
- [ ] No obvious N+1 query pattern introduced.
