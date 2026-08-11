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
| `quiz_attempts` | A student's in-progress-through-graded attempt at a quiz, with autosave and a start-time snapshot of question order/time limit |
| `quiz_attempt_answers` | Finalized per-question grading result within an attempt (score, correctness, AI feedback, topic tag) |
| `weak_topics` | Detected weak areas per student, tallied from `quiz_attempt_answers.topic_tag` misses |
| `study_sessions` | Study time/activity tracking |
| `conversations` | A chat thread scoped to one notebook + user |
| `messages` | Individual turns (user/assistant) within a conversation, with per-message citations |
| `images` | Reserved; not built. Retrieved topic images (`TaskType.TOPIC_IMAGE_SEARCH`, ADR 0010) are not persisted here — they're cached in Redis only (`ai/image_search/cache.py`, 24h TTL), not written to Postgres |
| `embeddings` | Vector embeddings (pgvector) linked to source chunks |
| `progress` / `analytics` | Rolled-up performance metrics |
| `search_cache` | Reserved; not built. Internet search results (`TaskType.INTERNET_SEARCH`, ADR 0012) are cached in Redis instead (`ai/internet_search/cache.py`, per-provider TTL) — a general Postgres-backed cache table was explicitly rejected as premature in ADR 0012's Alternatives Considered |
| `generated_materials` | NotebookLM Studio artifacts (audio/report/slides/infographic/mindmap/data_table) — one polymorphic table rather than six near-duplicate ones |

### Relationships (high level)
`users` own `documents` (`uploaded_by`, `ON DELETE CASCADE`) and `notebooks` (`owner_id`, `ON DELETE CASCADE`) directly — both `documents.subject_id` and `notebooks.subject_id` are optional (`ON DELETE SET NULL`), so a document/notebook survives its subject being deleted and isn't required to belong to one. A `document` is either file-backed (`storage_path` set) or link-backed (`source_url` set, e.g. a pasted URL) — exactly one of the two, enforced by a CHECK constraint — and both kinds carry the same optional `title`/`description` resource metadata (falls back to `filename` when unset). `notebook_sources` is the join between `notebooks` and `documents` (both `ON DELETE CASCADE` — deleting either side removes the join row), unique on `(notebook_id, document_id)` — this is what makes a notebook's "Resources" tab a one-notebook-to-many-documents relationship — and carries its own NotebookLM indexing lifecycle independent of the document's parse lifecycle. `notebook_sources` → `embeddings` (once chunking/embedding lands). `quizzes` → `questions` → `quiz_attempts` → `weak_topics`/`progress`. `conversations` belong to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`); `messages` belong to one `conversations` row (`ON DELETE CASCADE`) and carry `role` (`user`/`assistant`), `content`, `provider`, and a `citations` JSONB array (`source_id`/`chunk_id`/`excerpt` per entry) so grounding survives per message rather than per conversation. `notes` and `flashcard_sets` each belong to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`) and share the same async-generation shape: a `status` enum (`pending`/`generating`/`done`/`failed`), `error_message`, and generated content populated once a Celery task completes — `notes.material_type` picks one of two output shapes: four values (`note`/`study_guide`/`cheat_sheet`/`formula_sheet`) populate `content` (Markdown); three values (`mnemonics`/`timeline`/`comparison_chart`) populate `content_json` (JSONB — a list for the first two, a single `{subjects, attributes, rows}` object for the last) instead, leaving `content` null — both share the same `citations` JSONB array. `flashcard_sets` holds no content itself but owns `flashcards` (`ON DELETE CASCADE`, ordered by `position`), each with `front`/`back`/a single `citation` JSONB object. `generated_materials` belongs to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`), shares the same `status`/`error_message` async-generation shape, and carries an `artifact_type` enum plus a generic `options` JSONB (type-specific generation params — format/length/orientation/etc, validated at the API layer, not the schema, so a new NotebookLM option never needs a migration) — its result lands in exactly one of `content` (Text — `report` markdown or `mindmap` JSON) or `storage_path`/`mime_type` (this app's own `FileStorage`, populated for the four binary types; never a NotebookLM-hosted URL) depending on `artifact_type`.

`quizzes` belongs to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`) and shares the same async-generation shape as `notes`/`flashcard_sets`/`generated_materials`: a `status` enum (`pending`/`generating`/`done`/`failed`) plus `error_message`. It additionally carries the generation request itself — `topic` (nullable), `question_types` (JSONB list of requested type strings), `question_count`, `difficulty` (enum `easy`/`medium`/`hard`/`mixed`), and an optional `time_limit_seconds`. `quizzes` owns `questions` (`ON DELETE CASCADE`, ordered by `position`), each with a `question_type` enum (`mcq`/`true_false`/`fill_blank`/`matching`/`assertion_reason`/`short_answer`/`long_answer`/`case_study`), `prompt` (Text), a generic `type_data` JSONB (shape — options/pairs/blanks — varies per `question_type`, validated at the API/Pydantic layer, not the schema, same pattern as `generated_materials.options`), `explanation` (Text, always populated), a per-question `difficulty` (same enum as `quizzes.difficulty`, since a `mixed` quiz varies difficulty per question), a nullable `topic` (Text, free-form — distinct from the quiz-level `quizzes.topic` generation request; populated per-question at generation time to feed weak-topic tagging for objective types, which otherwise have no other topic source at grading time, see `docs/adr/0011-quiz-evaluation-scoring-design.md` decision #3), and a nullable `citation` JSONB object (source chunk reference, same shape as `flashcards.citation`). Exactly one of `correct_answer` (JSONB, objective types) or `reference_answer` (Text, free-text types) is populated depending on `question_type` — enforced at the API layer, not a DB constraint.

`quiz_attempts` is the quiz-taking/evaluation engine built on top of `quizzes`/`questions` (a separate migration from the quiz-definition tables): one row per student attempt, belonging to one `quizzes` row and one `users` row (both `ON DELETE CASCADE`). A `status` enum (`in_progress`/`submitted`/`grading`/`graded`/`abandoned`) tracks its lifecycle, `started_at`/`submitted_at`/`graded_at` its timestamps, and `time_limit_seconds`/`question_order` are snapshots taken at attempt-start time (copied from `quizzes.time_limit_seconds` and a randomized question id order respectively) so a later edit to the quiz — or its questions — never retroactively changes an attempt already underway. `answers` is a scratch JSONB autosave column keyed by `question_id`, holding pre-submit in-progress answers; `score`/`max_score` are nullable numerics populated once grading completes. `quiz_attempts` owns `quiz_attempt_answers` (`ON DELETE CASCADE`), the finalized per-question record written once grading runs: `student_answer` (JSONB), `is_correct` (nullable bool, objective types), `score` (numeric, defaults `0`), `ai_feedback` (nullable text), and `topic_tag` (nullable text, free-form — not an FK, since a question can span topics that don't map 1:1 to a fixed taxonomy) which feeds `weak_topics` detection. `quiz_attempt_answers` also belongs to one `questions` row (`ON DELETE CASCADE`). `weak_topics` is deliberately minimal — a per-`(user, notebook)` tally of missed topics (`topic` text, `missed_count` int, `last_detected_at` nullable timestamp), both FKs `ON DELETE CASCADE` — broader progress/analytics rollups are a separate, not-yet-implemented later roadmap item, not this table's concern.

Full ERD to be added once schema stabilizes.

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
