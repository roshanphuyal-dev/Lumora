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

### Phase 1 — Foundation (Status: Done)
- Authentication (login, register, Google login, profiles)
- Dashboard skeleton
- File upload (PDF/PPTX/DOCX/images) + parsing
- NotebookLM integration (document indexing)
- Gemini integration (basic teaching calls)

Verified end-to-end against a running backend + real providers (no stubs remaining). Deployment (CI/CD, live hosting) is intentionally not a gate for this status — see Phase 5 and the Definition of Done note below.

### Phase 2 — Study Materials (Status: Not Started)
- Notes, study guides, flashcards
- AI chat (basic Q&A grounded in notebook) — streaming + persisted history architecture pre-specified in [ADR 0009](adr/0009-ai-chat-streaming-persistence-export.md)
- Knowledge base UI (notebook/source management)

### Phase 3 — Assessment (Status: Not Started)
- Quiz generation (all question types)
- Quiz engine (timer, navigation, autosave, review)
- AI evaluation (scoring, feedback, weak-topic tagging)
- Internet search integration (Tavily/Brave)
- Image retrieval (Wikimedia/Openverse/Unsplash) — architecture pre-specified in [ADR 0010](adr/0010-topic-image-retrieval.md)

### Phase 4 — Personalization (Status: Not Started)
- Full RAG pipeline across notebooks
- Long-term memory (per-student weak topics, history)
- Adaptive difficulty tutoring
- Citation system end-to-end

### Phase 5 — Expansion (Status: Not Started)
- Voice tutor, AI whiteboard, mobile app
- YouTube summarizer, research assistant, coding tutor, math solver
- AI debate mode, AI mock exams
- **Deployment**: CI/CD (GitHub Actions), live hosting (Oracle Cloud VPS, Docker, Nginx) per `docs/DEPLOYMENT.md`. Deliberately moved here from being a per-phase gate (previously blocked Phase 1's Definition of Done) — the app runs and is verified end-to-end locally/against real providers through Phases 1-4; going live is treated as its own phase of work, not a checkbox on every earlier one.

## Definition of Done (per phase)
A phase is Done when: its features work end-to-end against real providers/a running local backend (not a deployed environment — see Phase 5), have test coverage per `docs/TESTING.md`, and their `docs/*.md` sections are updated to reflect the shipped implementation (not the original plan).

<!-- TODO: assign target dates once solo/team capacity is known -->
