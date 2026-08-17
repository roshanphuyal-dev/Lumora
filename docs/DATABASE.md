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
| `document_sections` | Parser-preserved natural units (for example PDF pages and PPTX slides) used for citation locators |
| `chunks` | Ordered, content-hashed retrieval units linked to documents and optional natural sections; includes an English generated full-text search vector |
| `notebooks` | Knowledge-base containers grouping related sources |
| `notebook_sources` | Join: which documents/sources belong to which notebook |
| `notes` | Generated notes/study guides/cheat sheets/formula sheets/mnemonics/timelines/comparison charts (`NoteMaterialType`), with async generation status and citations |
| `flashcard_sets` | A generated flashcard set, with async generation status |
| `flashcards` | Individual front/back cards within a flashcard set, with per-card citation |
| `quizzes` / `questions` | Quiz definitions and their questions |
| `quiz_attempts` | A student's in-progress-through-graded attempt at a quiz, with autosave and a start-time snapshot of question order/time limit |
| `quiz_attempt_answers` | Finalized per-question grading result within an attempt (score, correctness, AI feedback, topic tag) |
| `learning_evidence` | Immutable, structured per-answer learning evidence used for deterministic mastery |
| `topic_masteries` | Latest persisted notebook/topic mastery and confidence snapshot |
| `learning_preferences` | Explicit user-confirmed tutoring depth and style preferences |
| `learning_preference_suggestions` | Deterministic pending/accepted/rejected preference suggestions; pending rows never affect prompts |
| `weak_topics` | Detected weak areas per student, tallied from `quiz_attempt_answers.topic_tag` misses |
| `study_activities` | Immutable, idempotent study-time and factual revision activity events |
| `conversations` | A chat thread scoped to one notebook + user |
| `messages` | Individual turns (user/assistant) within a conversation, with grounding kind, citations, and an optional attached image result |
| `images` | Reserved; not built. Retrieved topic images are cached in Redis globally and, when attached in chat, stored as JSONB on the corresponding `messages` row |
| `embeddings` | Versioned 768-dimensional pgvector embeddings linked to source chunks |
| `progress` / `analytics` | Rolled-up performance metrics |
| `search_cache` | Reserved; not built. Internet search results (`TaskType.INTERNET_SEARCH`, ADR 0012) are cached in Redis instead (`ai/internet_search/cache.py`, per-provider TTL) — a general Postgres-backed cache table was explicitly rejected as premature in ADR 0012's Alternatives Considered |
| `generated_materials` | NotebookLM Studio artifacts (audio/report/slides/infographic/mindmap/data_table) — one polymorphic table rather than six near-duplicate ones |

### Relationships (high level)
`users` own `documents` (`uploaded_by`, `ON DELETE CASCADE`) and `notebooks` (`owner_id`, `ON DELETE CASCADE`) directly — both `documents.subject_id` and `notebooks.subject_id` are optional (`ON DELETE SET NULL`), so a document/notebook survives its subject being deleted and isn't required to belong to one. A `document` is either file-backed (`storage_path` set) or link-backed (`source_url` set, e.g. a pasted URL) — exactly one of the two, enforced by a CHECK constraint — and both kinds carry the same optional `title`/`description` resource metadata (falls back to `filename` when unset). Its parse lifecycle remains separate from its local RAG lifecycle (`pending`/`indexing`/`indexed`/`failed`). A document owns ordered `document_sections` and `chunks` (`ON DELETE CASCADE`); a chunk may point to a natural section (`ON DELETE SET NULL`) and owns versioned `embeddings` (`ON DELETE CASCADE`). `notebook_sources` is the join between `notebooks` and `documents` (both `ON DELETE CASCADE` — deleting either side removes the join row), unique on `(notebook_id, document_id)` — this is what makes a notebook's "Resources" tab a one-notebook-to-many-documents relationship — and carries its own NotebookLM indexing lifecycle and optional provider-native source identifier independent of the document's parse and local-RAG lifecycles. `quizzes` → `questions` → `quiz_attempts` → `weak_topics`/`progress`. `conversations` belong to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`); `messages` belong to one `conversations` row (`ON DELETE CASCADE`) and carry `role` (`user`/`assistant`), `kind` (`notebook`/`web_search`/`paper_search`, default `notebook`), `content`, `provider`, a `citations` JSONB array (`source_id`/`chunk_id`/`excerpt` per entry), and a nullable `image_result` JSONB object (`image_url`, `attribution`, `license`, `source_url`). `web_search` and `paper_search` messages share the same `content`/`citations`/`provider` shape and need no dedicated structured column; `image_result` stays specific to image search results. Keeping grounding kind and image attribution on the message makes both render correctly after conversation rehydration. `notes` and `flashcard_sets` each belong to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`) and share the same async-generation shape: a `status` enum (`pending`/`generating`/`done`/`failed`), `error_message`, and generated content populated once a Celery task completes — `notes.material_type` picks one of two output shapes: four values (`note`/`study_guide`/`cheat_sheet`/`formula_sheet`) populate `content` (Markdown); three values (`mnemonics`/`timeline`/`comparison_chart`) populate `content_json` (JSONB — a list for the first two, a single `{subjects, attributes, rows}` object for the last) instead, leaving `content` null — both share the same `citations` JSONB array. `flashcard_sets` holds no content itself but owns `flashcards` (`ON DELETE CASCADE`, ordered by `position`), each with `front`/`back`/a single `citation` JSONB object. `generated_materials` belongs to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`), shares the same `status`/`error_message` async-generation shape, and carries an `artifact_type` enum plus a generic `options` JSONB (type-specific generation params — format/length/orientation/etc, validated at the API layer, not the schema, so a new NotebookLM option never needs a migration) — its result lands in exactly one of `content` (Text — `report` markdown or `mindmap` JSON) or `storage_path`/`mime_type` (this app's own `FileStorage`, populated for the four binary types; never a NotebookLM-hosted URL) depending on `artifact_type`.

`quizzes` belongs to one `notebooks` row and one `users` row (both `ON DELETE CASCADE`) and shares the same async-generation shape as `notes`/`flashcard_sets`/`generated_materials`: a `status` enum (`pending`/`generating`/`done`/`failed`) plus `error_message`. It additionally carries the generation request itself — `topic` (nullable), `question_types` (JSONB list), `question_count`, `difficulty`, optional `time_limit_seconds`, and `include_web_search`. `adaptation_applied` and nullable `adaptive_difficulty_mix` record whether personalization changed a newly generated mixed quiz and the exact easy/medium/hard counts requested; they never alter existing attempts. `quizzes` owns `questions` (`ON DELETE CASCADE`, ordered by `position`), each with its typed prompt data, answer/reference answer, explanation, difficulty, topic, and nullable citation.

`quiz_attempts` is the quiz-taking/evaluation engine built on top of `quizzes`/`questions` (a separate migration from the quiz-definition tables): one row per student attempt, belonging to one `quizzes` row and one `users` row (both `ON DELETE CASCADE`). A `status` enum (`in_progress`/`submitted`/`grading`/`graded`/`abandoned`) tracks its lifecycle, `started_at`/`submitted_at`/`graded_at` its timestamps, and `time_limit_seconds`/`question_order` are snapshots taken at attempt-start time (copied from `quizzes.time_limit_seconds` and a randomized question id order respectively) so a later edit to the quiz — or its questions — never retroactively changes an attempt already underway. `answers` is a scratch JSONB autosave column keyed by `question_id`, holding pre-submit in-progress answers; `score`/`max_score` are nullable numerics populated once grading completes. `quiz_attempts` owns `quiz_attempt_answers` (`ON DELETE CASCADE`), the finalized per-question record written once grading runs: `student_answer` (JSONB), `is_correct` (nullable bool, objective types), `score` (numeric, defaults `0`), `ai_feedback` (nullable text), and `topic_tag` (nullable text, free-form — not an FK, since a question can span topics that don't map 1:1 to a fixed taxonomy) which feeds `weak_topics` detection. `quiz_attempt_answers` also belongs to one `questions` row (`ON DELETE CASCADE`). `weak_topics` remains the historical missed-topic tally.

When personalization is enabled, completing grading writes one idempotent `learning_evidence` row per tagged answer in the same transaction as the final grade. Each row snapshots the owner, notebook, answer, topic, question difficulty, normalized 0–1 score, and observation time; it is deleted with the answer/notebook/user. `topic_masteries` is unique by `(user_id, notebook_id, topic)` and stores the latest derived mastery, confidence, total decayed evidence weight, evidence count, and calculation time. Reads recalculate recency decay from the immutable evidence so a stored snapshot cannot freeze as evidence ages. Both tables have composite owner/notebook/topic indexes, and all queries additionally enforce notebook ownership.

`study_activities` stores factual, immutable activity events scoped directly to a user and notebook (both `ON DELETE CASCADE`). A per-user `activity_key` makes retries idempotent. Each event records a bounded duration (0–14,400 seconds), UTC occurrence time, activity type (`study_session`, `material_viewed`, `material_revised`, or system-authored `quiz_completed`), and an optional resource type/id pair. Graded quiz completion is written transactionally using the attempt id as its activity key; authenticated clients may report the other three types through the bounded API. Streaks, time totals, revision history, and heatmaps are derived from these events rather than stored as mutable counters.

`learning_preferences` is unique by `user_id` and stores only explicit explanation depth and style choices. `learning_preference_suggestions` records the fixed behavioral signal, suggested field/value, rationale, and resolution status. Suggestions are owner-scoped and have no effect until accepted; acceptance copies the validated value into `learning_preferences`. Deterministic recommendations are computed from owner-scoped `topic_masteries` at read time, so no recommendation table or model-authored decision state is persisted.

Full ERD to be added once schema stabilizes.

### Indexing Strategy
- `embeddings.vector` uses pgvector's 768-dimensional `vector` type and an HNSW cosine-distance index (`m=16`, `ef_construction=64` initially; tune against the retrieval-evaluation fixture).
- `chunks.search_vector` is a stored generated `tsvector` using PostgreSQL's English text-search configuration and a GIN index for lexical retrieval.
- Standard B-tree indexes on all foreign keys and frequently filtered columns (`user_id`, `notebook_id`, `created_at`).

### Migration Conventions
- Alembic, one migration per PR that changes schema.
- Autogenerate (`uv run alembic revision --autogenerate -m "..."`), then hand-review the generated diff before committing.
- Never edit a migration that has been merged/deployed — write a new one.
- Destructive migrations (drop column/table) require a backup/rollback note in the migration docstring and a mention in `CHANGELOG.md`.

<!-- TODO: add full ERD diagram once Phase 1 schema is implemented -->
<!-- TODO: document chosen pgvector index type + distance metric once tuned -->
