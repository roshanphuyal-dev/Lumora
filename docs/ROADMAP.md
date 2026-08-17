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

### Phase 3 — Assessment (Status: Done)
- Quiz generation — done, 8 of 8 DB-supported question types actually generatable, including `assertion_reason` (schema-validated at generation time, see `docs/FEATURES.md`'s Quiz Generator section); grounded via NotebookLM retrieval + Gemini structured output (`TaskType.QUIZ_GENERATION`, `docs/AI.md#routing-logic`)
- Quiz engine (timer, navigation, autosave, review) — done (`QuizTakingView`/`QuizReviewView`, `docs/FEATURES.md`); adaptive question *selection* is not part of this — only difficulty *tagging* at generation time exists, deferred to Phase 4 below
- AI evaluation (scoring, feedback, weak-topic tagging) — done for objective (deterministic) and free-text (AI-graded, [ADR 0011](adr/0011-quiz-evaluation-scoring-design.md)) scoring/feedback; weak-topic tagging now covers both — objective types via `Question.topic` set at generation time, free-text via `QUIZ_GRADING`'s `topic_tag` (`docs/FEATURES.md`'s AI Evaluation section)
- Internet search integration (Tavily/Brave) — done, end-to-end (`TaskType.INTERNET_SEARCH`, [ADR 0012](adr/0012-internet-search-integration.md)): Tavily primary, Brave optional fallback, Gemini synthesizes a cited answer from normalized results; `POST /notebooks/{id}/search` and a "Search the web" toggle on the Ask tab surface it to students (`docs/FEATURES.md`'s Internet Research section)
- Image retrieval (Wikimedia/Openverse) — done, end-to-end ([ADR 0010](adr/0010-topic-image-retrieval.md)): Wikimedia Commons primary, Openverse fallback, pure retrieval (no synthesis); `POST /notebooks/{id}/image-search` and a per-message "Find an image" action surface it (`docs/FEATURES.md`'s Internet Research section). Unsplash was never added as a provider — two keyless/low-friction providers (`ADR 0010`'s Decision) were judged sufficient
- Quiz generation wired to web-search grounding — done: opt-in `Quiz.include_web_search` runs `TaskType.INTERNET_SEARCH` alongside NotebookLM retrieval, merged into generation context (`docs/FEATURES.md`'s Quiz Generator section, `docs/AI_WORKFLOWS.md#3`)
- Research paper search — done, closing this Definition of Done gap ([ADR 0013](adr/0013-paper-search-integration.md)): `TaskType.PAPER_SEARCH`, arXiv primary, Semantic Scholar optional fallback, same synthesis shape as `INTERNET_SEARCH`; exposed via both a stateless and a persisted conversation-scoped endpoint, and a 3-way Notebook/Web/Papers toggle on the Ask tab (`docs/FEATURES.md`'s Internet Research section)

Both of this Definition of Done's code-resolvable gaps (quiz+search wiring, research paper search) are now closed (257 → 319 passing backend tests; frontend lint/tsc/test clean). Two items remain open, neither a code blocker: Tavily's privacy-policy-vs-FAQ ambiguity and Semantic Scholar's default non-commercial license both require written clarification from the provider before real student-derived queries reach them (`docs/SECURITY.md`, `ADR 0012`, `ADR 0013`) — pre-production gates the user still needs to pursue, not something a code change resolves. The quiz-taking UI also remains not manually verified in a running browser (no connected Chrome extension during the milestones that built it) — Vitest/RTL coverage exists (`QuizTakingView`/`AnswerReview` tests, `docs/TESTING.md`) but isn't a substitute for that still-outstanding manual pass.

### Phase 4 — Personalization (Status: In Progress)
- Implemented behind default-off `RAG_ENABLED` / `PERSONALIZATION_ENABLED` gates: semantic chunks and 768-dimensional embeddings, owner-scoped hybrid retrieval with reciprocal-rank fusion, NotebookLM-first fallback routing, authoritative citation resolution, and clickable local citation panels across generated-content surfaces.
- Implemented and database-tested: graded-answer evidence, recency/difficulty-weighted topic mastery, progress and quiz-performance APIs, explicit learning preferences, deterministic pending suggestions with accept/reject, deterministic recommendations, and mastery-band adaptation for newly generated mixed quizzes. Pending suggestions never affect prompts; active attempts are never mutated.
- Implemented frontend surfaces: mastery/progress dashboard, quiz trends, preference controls and suggestions, recommendations, and adaptation status.
- Remaining before **Done**: apply migrations and exercise the complete flow in a clean full-stack environment; manually verify responsive/light/dark UI; exercise live NotebookLM/Gemini embedding and generation paths with both flags enabled; tune retrieval against the checked-in evaluation fixture. Study-time tracking, UTC-date streaks, factual revision history, and learning heatmap APIs are implemented; their final frontend verification remains part of the full-stack pass.

### Phase 5 — Expansion (Status: Not Started)
- Voice tutor, AI whiteboard, mobile app
- YouTube summarizer, research assistant, coding tutor, math solver
- AI debate mode, AI mock exams
- **Deployment**: CI/CD (GitHub Actions), live hosting (Oracle Cloud VPS, Docker, Nginx) per `docs/DEPLOYMENT.md`. Deliberately moved here from being a per-phase gate (previously blocked Phase 1's Definition of Done) — the app runs and is verified end-to-end locally/against real providers through Phases 1-4; going live is treated as its own phase of work, not a checkbox on every earlier one.

## Definition of Done (per phase)
A phase is Done when: its features work end-to-end against real providers/a running local backend (not a deployed environment — see Phase 5), have test coverage per `docs/TESTING.md`, and their `docs/*.md` sections are updated to reflect the shipped implementation (not the original plan).

<!-- TODO: assign target dates once solo/team capacity is known -->
