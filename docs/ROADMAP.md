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

### Phase 2 — Study Materials (Status: Done)
- Notes, study guides, flashcards — done, async generation grounded via NotebookLM + Gemini (structured output for flashcards), per `docs/AI_WORKFLOWS.md#1`/`#2`
- AI chat (basic Q&A grounded in notebook) — done, per [ADR 0009](adr/0009-ai-chat-streaming-persistence-export.md)
- Knowledge base UI (notebook/source management and notebook search) — done
- NotebookLM Studio artifacts (audio overview, report, slide deck, infographic, mind map, data table) — done, additive scope beyond this phase's original gate, closing most of the `docs/FEATURES.md` "Study Material Generator" catalogue via NotebookLM's own Studio feature rather than a custom pipeline
- Cheat sheets, formula sheets, mnemonics, timelines, comparison charts — done, the remaining additive scope; a custom Gemini pipeline (extending Notes' existing `NoteMaterialType`/generation infra) since none of these map to a Studio artifact type. `docs/FEATURES.md`'s "Study Material Generator" catalogue is now fully built.

Verified end-to-end against a running backend + real providers (Postgres, Redis/Celery, live Gemini calls, live NotebookLM Studio generation) — see the Definition of Done note below.

### Phase 3 — Assessment (Status: In Progress)
- Quiz generation — done, 7 of 8 DB-supported question types actually generatable (`assertion_reason` has schema/grading/UI support but is excluded from generation, so unreachable — see `docs/FEATURES.md`'s Quiz Generator section for the precise breakdown); grounded via NotebookLM retrieval + Gemini structured output (`TaskType.QUIZ_GENERATION`, `docs/AI.md#routing-logic`)
- Quiz engine (timer, navigation, autosave, review) — done (`QuizTakingView`/`QuizReviewView`, `docs/FEATURES.md`); adaptive question *selection* is not part of this — only difficulty *tagging* at generation time exists, deferred to Phase 4 below
- AI evaluation (scoring, feedback, weak-topic tagging) — done for objective (deterministic) and free-text (AI-graded, [ADR 0011](adr/0011-quiz-evaluation-scoring-design.md)) scoring/feedback; weak-topic tagging is **partial** — it only fires for free-text/AI-graded answers, since `Question` has no topic column for objective types (`docs/FEATURES.md`'s AI Evaluation section)
- Internet search integration (Tavily/Brave) — not started
- Image retrieval (Wikimedia/Openverse/Unsplash) — not started; architecture pre-specified in [ADR 0010](adr/0010-topic-image-retrieval.md)

Not Done per this doc's own Definition of Done below: the two not-started sub-items above remain, and the quiz-taking UI has never been manually verified in a running browser (no connected Chrome extension during the milestones that built it) — shipped features are otherwise tested (189 passing backend/service tests) and their docs are current, but frontend test coverage for the quiz UI specifically is zero (Vitest/RTL infra itself deferred, `docs/TESTING.md`).

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
