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
- **Grounding** — the property of an AI response being traceable to specific Source/Chunk citations, as opposed to unattributed generic model knowledge.

<!-- Add a term here the first time it's used ambiguously across two or more docs. -->
