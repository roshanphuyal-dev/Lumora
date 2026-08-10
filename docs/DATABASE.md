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
| `documents` | Uploaded files or linked URLs + extracted metadata |
| `notebooks` | Knowledge-base containers grouping related sources |
| `notebook_sources` | Join: which documents/sources belong to which notebook |
| `notes` | Generated notes/study guides/cheat sheets/formula sheets/mnemonics/timelines/comparison charts (`NoteMaterialType`), with async generation status and citations |
| `flashcard_sets` | A generated flashcard set, with async generation status |
| `flashcards` | Individual front/back cards within a flashcard set, with per-card citation |
| `quizzes` / `questions` | Quiz definitions and their questions |
| `quiz_attempts` | Student submissions + scores |
| `weak_topics` | Detected weak areas per student |
| `study_sessions` | Study time/activity tracking |
| `conversations` | A chat thread scoped to one notebook + user |
| `messages` | Individual turns (user/assistant) within a conversation, with per-message citations |
| `images` | Retrieved/cached image references |
| `embeddings` | Vector embeddings (pgvector) linked to source chunks |
| `progress` / `analytics` | Rolled-up performance metrics |
| `search_cache` | Cached search API results |
| `generated_materials` | NotebookLM Studio artifacts (audio/report/slides/infographic/mindmap/data_table) — one polymorphic table rather than six near-duplicate ones |

### Relationships (high level)
`users` own `documents` (`uploaded_by`, `ON DELETE CASCADE`) and `notebooks` (`owner_id`, `ON DELETE CASCADE`) directly — both `documents.subject_id` and `notebooks.subject_id` are optional (`ON DELETE SET NULL`), so a document/notebook survives its subject being deleted and isn't required to belong to one. A `document` is either file-backed (`storage_path` set) or link-backed (`source_url` set, e.g. a pasted URL) — exactly one of the two, enforced by a CHECK constraint — and both kinds carry the same optional `title`/`description` resource metadata (falls back to `filename` when unset). `notebook_sources` is the join between `notebooks` and `documents` (both `ON DELETE CASCADE` — deleting either side removes the join row), unique on `(notebook_id, document_id)` — this is what makes a notebook's "Resources" tab a one-notebook-to-many-documents relationship — and carries its own NotebookLM indexing lifecycle independent of the document's parse lifecycle. `notebook_sources` → `embeddings` (once chunking/embedding lands). `quizzes` → `questions` → `quiz_attempts` → `weak_topics`/`progress`. `conversations` belong to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`); `messages` belong to one `conversations` row (`ON DELETE CASCADE`) and carry `role` (`user`/`assistant`), `content`, `provider`, and a `citations` JSONB array (`source_id`/`chunk_id`/`excerpt` per entry) so grounding survives per message rather than per conversation. `notes` and `flashcard_sets` each belong to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`) and share the same async-generation shape: a `status` enum (`pending`/`generating`/`done`/`failed`), `error_message`, and generated content populated once a Celery task completes — `notes.material_type` picks one of two output shapes: four values (`note`/`study_guide`/`cheat_sheet`/`formula_sheet`) populate `content` (Markdown); three values (`mnemonics`/`timeline`/`comparison_chart`) populate `content_json` (JSONB — a list for the first two, a single `{subjects, attributes, rows}` object for the last) instead, leaving `content` null — both share the same `citations` JSONB array. `flashcard_sets` holds no content itself but owns `flashcards` (`ON DELETE CASCADE`, ordered by `position`), each with `front`/`back`/a single `citation` JSONB object. `generated_materials` belongs to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`), shares the same `status`/`error_message` async-generation shape, and carries an `artifact_type` enum plus a generic `options` JSONB (type-specific generation params — format/length/orientation/etc, validated at the API layer, not the schema, so a new NotebookLM option never needs a migration) — its result lands in exactly one of `content` (Text — `report` markdown or `mindmap` JSON) or `storage_path`/`mime_type` (this app's own `FileStorage`, populated for the four binary types; never a NotebookLM-hosted URL) depending on `artifact_type`. Full ERD to be added once schema stabilizes.

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
