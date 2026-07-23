# Token & Cost Optimization

## Purpose

The strategy reference for keeping AI spend low without degrading quality — caching, routing, prompt design, and storage tactics specifically aimed at reducing tokens/cost. Complements `docs/OBSERVABILITY.md`, which covers *watching* the cost/usage numbers this doc tries to keep down.

## What Belongs Here

- Concrete cost-reduction tactics, grouped by category.
- Caching policy for AI outputs specifically.

## What Never Belongs Here

- Monitoring/alerting/dashboards for cost (`OBSERVABILITY.md`).
- Routing *logic* (which model handles which task — `AI.md`); this doc only covers *why that's cheaper*.

## Structure

### Request Optimization
Cache identical prompts. Chunk documents intelligently. Send only relevant chunks (RAG) instead of full documents. Use NotebookLM retrieval before invoking Gemini. Reuse NotebookLM summaries across features. Compress conversation history before reuse. Prefer structured JSON responses over free text (cheaper to parse, less filler). Strip redundant context before sending.

### Model Optimization
Route by task cost/complexity (`docs/AI.md#routing-logic`): small/cheap model for formatting, medium for summaries, NotebookLM for document understanding, Gemini for complex reasoning/teaching. Never default to the most expensive model "to be safe" — route deliberately.

### Prompt Optimization
Reusable prompt templates (`docs/PROMPTS.md`), cached system prompts, function calling over free-text parsing, minimal few-shot examples, composable prompt fragments instead of copy-pasted blocks.

### Storage Optimization
Store embeddings once, never regenerate for unchanged content. Cache NotebookLM outputs, notes, quizzes, flashcards, search results, images, and generated LaTeX — keyed by content hash + generation parameters so identical requests are served from cache.

### Processing Optimization
Background indexing (don't block the request). Incremental notebook updates (don't re-index unchanged sources). Parallel retrieval where independent. Batch embedding generation. Delta document updates. Asynchronous processing via Celery for anything non-trivial.

### Cost Monitoring (pointer)
Token tracking, daily budgets, per-model usage analytics, automatic fallback, rate limiting — these are *implemented* per this doc's tactics but *observed* via `docs/OBSERVABILITY.md`'s dashboards. Don't duplicate dashboard design here.

<!-- TODO: define cache key scheme (content hash + params) once caching layer is implemented -->
<!-- TODO: set concrete daily token budgets once usage baseline exists -->
