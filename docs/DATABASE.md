# Database

## Purpose

The system-of-record schema reference: tables, relationships, indexing/vector-search strategy, migration conventions.

## What Belongs Here

- Table list with purpose and key relationships.
- Indexing strategy, especially `pgvector` usage.
- Migration workflow conventions.

## What Never Belongs Here

- API contracts (`API.md`).
- AI/embedding *generation* logic (`AI.md`) — this doc covers storage, not how embeddings are produced.
- ORM code samples — the code is the source of truth for exact columns; this doc stays at the ERD/relationship level so it doesn't rot every migration.

## Structure

### Engine
PostgreSQL via Supabase, `pgvector` extension enabled for embeddings. SQLAlchemy models + Alembic migrations (`backend/`).

### Core Tables (purpose, not full column spec)

| Table | Purpose |
|---|---|
| `users` | Accounts, auth, profile |
| `courses` / `subjects` | Organizational grouping for a student's material |
| `documents` | Uploaded files + extracted metadata |
| `notebooks` | Knowledge-base containers grouping related sources |
| `notebook_sources` | Join: which documents/sources belong to which notebook |
| `notes` | Generated notes/study guides |
| `flashcards` | Generated flashcard sets |
| `quizzes` / `questions` | Quiz definitions and their questions |
| `quiz_attempts` | Student submissions + scores |
| `weak_topics` | Detected weak areas per student |
| `study_sessions` | Study time/activity tracking |
| `ai_chats` | Chat history per notebook/session |
| `images` | Retrieved/cached image references |
| `embeddings` | Vector embeddings (pgvector) linked to source chunks |
| `progress` / `analytics` | Rolled-up performance metrics |
| `search_cache` | Cached search API results |
| `generated_materials` | Generic table for generated study materials not covered above |

### Relationships (high level)
`users` own `documents` (`uploaded_by`, `ON DELETE CASCADE`) and `notebooks` (`owner_id`, `ON DELETE CASCADE`) directly — both `documents.subject_id` and `notebooks.subject_id` are optional (`ON DELETE SET NULL`), so a document/notebook survives its subject being deleted and isn't required to belong to one. `notebook_sources` is the join between `notebooks` and `documents` (both `ON DELETE CASCADE` — deleting either side removes the join row), unique on `(notebook_id, document_id)`, and carries its own NotebookLM indexing lifecycle independent of the document's parse lifecycle. `notebook_sources` → `embeddings` (once chunking/embedding lands). `quizzes` → `questions` → `quiz_attempts` → `weak_topics`/`progress`. Full ERD to be added once schema stabilizes.

### Indexing Strategy
- `pgvector` HNSW/IVFFlat index on `embeddings.vector` scoped by notebook for retrieval performance (choice TBD at implementation, tradeoffs in ADR if changed later).
- Standard B-tree indexes on all foreign keys and frequently filtered columns (`user_id`, `notebook_id`, `created_at`).

### Migration Conventions
- Alembic, one migration per PR that changes schema.
- Autogenerate (`uv run alembic revision --autogenerate -m "..."`), then hand-review the generated diff before committing.
- Never edit a migration that has been merged/deployed — write a new one.
- Destructive migrations (drop column/table) require a backup/rollback note in the migration docstring and a mention in `CHANGELOG.md`.

<!-- TODO: add full ERD diagram once Phase 1 schema is implemented -->
<!-- TODO: document chosen pgvector index type + distance metric once tuned -->
