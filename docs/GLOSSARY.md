# Glossary

## Purpose

Canonical definitions for domain terms used across `docs/` and the codebase. This project has enough overloaded vocabulary (Document vs Source vs Notebook, Note vs Study Guide, etc.) that a shared glossary prevents naming drift as more docs and more contributors/agents accumulate over time.

## What Belongs Here

- One-paragraph definitions of domain nouns, disambiguating near-synonyms.

## What Never Belongs Here

- Implementation detail (link to the owning doc instead).
- Anything not actually ambiguous or overloaded — don't define generic terms (e.g. "user") that need no disambiguation.

## Terms

- **Document** — a single uploaded file (PDF/DOCX/PPTX/image) or linked URL, before it's associated with any Notebook. Owned by a user.
- **Source** — a Document once it has been added to a Notebook; the Notebook-scoped reference to the underlying Document, indexed by NotebookLM. **Resource** is the UI-facing label for the same thing (the notebook detail page's "Resources" tab) — use Source/Document in code and docs, Resource only in user-facing copy.
- **Notebook** — a knowledge-base container grouping related Sources for multi-document reasoning, retrieval, and citation (`docs/DATABASE.md#core-tables`).
- **Chunk** — a semantically coherent slice of a Source's extracted text, the unit that gets embedded and retrieved (`docs/AI.md#rag-design`).
- **Embedding** — the vector representation of a Chunk, stored in `pgvector` (`docs/DATABASE.md`).
- **Generated Material** — any AI-produced study artifact (notes, flashcards, quiz, study guide, mind map, etc.) — the generic table/category; specific types have their own tables where they need type-specific fields (`docs/DATABASE.md`).
- **Note** vs **Study Guide** — a Note is a single-topic or single-source summary; a Study Guide is a broader, often multi-source, exam-oriented compilation. Both are Generated Materials.
- **Orchestration Layer** — the backend component (`ai/orchestrator/`) that decides which AI provider handles a given request; see `docs/AI.md`.
- **Task Type** — the enum the Orchestration Layer uses to decide routing (`ai/orchestrator/task_types.py`, e.g. `document_index`, `notebook_query`, `teaching_explanation`) — declared by feature code, never a hardcoded provider choice.
- **Weak Topic** — a topic the student has demonstrated low mastery on, derived from quiz performance and tracked for adaptive tutoring (`docs/AI.md#memory--personalization`).
- **Quiz** vs **Question** vs **Attempt** — a Quiz is the generated definition (its topic, requested question types/count/difficulty, time limit); a Question is one item belonging to a Quiz (prompt, type, correct/reference answer); an Attempt is one student's run through a Quiz (a `quiz_attempts` row) — a single Quiz can have many Attempts (repeat/concurrent attempts are allowed), and an Attempt's per-question results live in `quiz_attempt_answers`, not on the Question itself, since the same Question is shared across every Attempt of its Quiz (`docs/DATABASE.md#core-tables`).
- **Grounding** — the property of an AI response being traceable to specific Source/Chunk citations, as opposed to unattributed generic model knowledge.
- **`Question.topic`** vs **`topic_tag`** vs **Weak Topic** — three related but distinct "topic" fields in the quiz pipeline: `Question.topic` is a per-question label set once at generation time (`ai/prompts/quiz_generation_v1.py`, every `question_type`); `QuizAttemptAnswer.topic_tag` is the per-answer label actually used for aggregation, copied from `Question.topic` for deterministically-graded types or set directly by the `QUIZ_GRADING` call for free-text types (`docs/adr/0011-quiz-evaluation-scoring-design.md`); **Weak Topic** (`weak_topics` table) is the aggregated running tally of missed `topic_tag`s per `(user, notebook)`. Don't conflate the per-question label with the per-answer or aggregated ones.
- **Search** — ambiguous between three distinct features as of ADR 0013: **Notebook Search** is retrieval scoped to a notebook's own indexed Sources (`docs/API.md`'s Notebook Search API); **Internet Search** is `TaskType.INTERNET_SEARCH` (ADR 0012, `docs/AI.md`) — a Tavily/Brave lookup against the open web, synthesized by Gemini; **Paper Search** is `TaskType.PAPER_SEARCH` (ADR 0013, `docs/AI.md`) — an arXiv/Semantic Scholar lookup against academic literature, same Gemini-synthesis shape as Internet Search but a distinct provider set and citation style. Internet and Paper Search are both surfaced via the Ask tab's Notebook/Web/Papers radio group (`AskNotebookSection.tsx`). Always qualify which one in code/docs/prompts; unqualified "search" is a code smell in this codebase now.
- **Image** — ambiguous between two distinct concepts: an **image Document** is a user-uploaded file (a photo/scan the student adds as a Source, same lifecycle as any other Document); a **topic image** is a Wikimedia/Openverse result retrieved on demand via `TaskType.TOPIC_IMAGE_SEARCH` (ADR 0010, `TopicImageResult`) and never persisted as a Document/Source — it's ephemeral, cached only in Redis (`docs/DATABASE.md#core-tables`), attached to a chat answer via the "Find an image" action.

<!-- Add a term here the first time it's used ambiguously across two or more docs. -->
