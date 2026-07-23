# Roadmap

## Purpose

Tracks *when* things get built, in phase order, with enough granularity to know what's in/out of scope for the current phase. Living document — update status as phases progress.

## What Belongs Here

- Phases, in dependency order, with concrete deliverables per phase.
- Phase status (Not Started / In Progress / Done).
- Explicit call-outs of what's deliberately deferred to a later phase.

## What Never Belongs Here

- Feature specs (`FEATURES.md`).
- Architecture rationale (`DECISIONS.md`/`adr/`).
- Day-to-day task tracking (use your issue tracker, not this file).

## Structure

### Phase 1 — Foundation (Status: In Progress)
- Authentication (login, register, Google login, profiles)
- Dashboard skeleton
- File upload (PDF/PPTX/DOCX/images) + parsing
- NotebookLM integration (document indexing)
- Gemini integration (basic teaching calls)

### Phase 2 — Study Materials (Status: Not Started)
- Notes, study guides, flashcards
- AI chat (basic Q&A grounded in notebook)
- Knowledge base UI (notebook/source management)

### Phase 3 — Assessment (Status: Not Started)
- Quiz generation (all question types)
- Quiz engine (timer, navigation, autosave, review)
- AI evaluation (scoring, feedback, weak-topic tagging)
- Internet search integration (Tavily/Brave)
- Image retrieval (Wikimedia/Openverse/Unsplash)

### Phase 4 — Personalization (Status: Not Started)
- Full RAG pipeline across notebooks
- Long-term memory (per-student weak topics, history)
- Adaptive difficulty tutoring
- Citation system end-to-end

### Phase 5 — Expansion (Status: Not Started)
- Voice tutor, AI whiteboard, mobile app
- YouTube summarizer, research assistant, coding tutor, math solver
- AI debate mode, AI mock exams

## Definition of Done (per phase)
A phase is Done when: its features work end-to-end in a deployed environment, have test coverage per `docs/TESTING.md`, and their `docs/*.md` sections are updated to reflect the shipped implementation (not the original plan).

<!-- TODO: assign target dates once solo/team capacity is known -->
