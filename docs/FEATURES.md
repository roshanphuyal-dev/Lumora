# Features

## Purpose

The detailed feature catalogue — one level more granular than `docs/PROJECT_PLAN.md`'s module overview, one level less granular than actual implementation tickets. The place to check "does this feature exist / is it planned" and which phase it belongs to.

## What Belongs Here

- Feature lists grouped by module, each tagged with its roadmap phase.
- Feature-level acceptance criteria where non-obvious.

## What Never Belongs Here

- Implementation detail (goes in the relevant `docs/*.md` — AI, DATABASE, API).
- Timeline/scheduling detail (`ROADMAP.md` owns phase-to-date mapping; this doc just tags phase).

## Structure

### Authentication (Phase 1)
Login, Register, Google Login, User Profiles.

### Dashboard (Phase 1–2)
Study statistics, current courses, daily goals, weak topics, recent activity, learning progress, AI recommendations.

### Document Processing (Phase 1)
PDF/PPTX/DOCX/image/URL upload, OCR, text extraction, metadata extraction.

### Notebook Knowledge Base (Phase 1–2)
Notebook creation, source management, multi-document indexing, citation management, knowledge retrieval/organization, notebook search.

### AI Processing (Phase 1–4)
Chunking, embeddings, context retrieval, RAG, NotebookLM retrieval, prompt builder, AI routing, AI generation. See `docs/AI.md`.

### Study Material Generator (Phase 2)
Done: Notes (detailed/revision), study guides, cheat sheets, formula sheets, mnemonics/memory tricks, timelines, and comparison charts (all seven Gemini-authored `NoteMaterialType` values, grounded via NotebookLM retrieval — the `notes` table and its generation pipeline, extended); flashcards (same pipeline family); mind maps, infographics, slide decks, reports, audio summaries, and data tables (NotebookLM Studio-authored — see `docs/AI.md`/`docs/API.md`'s Studio API).

The full catalogue is now covered — nothing left unbuilt under this heading.

### Quiz Generator (Phase 3)
Done: generation UI (`QuizzesSection`, notebook detail page) creates a quiz grounded via NotebookLM retrieval, async (`status: pending → generating → done/failed`, `docs/API.md`'s Quiz API). **8 of 8 DB-supported question types are actually generatable**: mcq, true/false, fill-in-blank, matching, assertion-reason, short answer, long answer, case study (`ai/orchestrator/schemas.py:QUESTION_TYPES`, `docs/AI.md#routing-logic`). `assertion_reason` generation is schema-validated: `_validate_assertion_reason_items` (`ai/orchestrator/orchestrator.py`) rejects any generated item whose `options`/`correct_answer` drift from the canonical 4-string `ASSERTION_REASON_OPTIONS` set, raising rather than silently persisting an ungradeable question. "Scenario questions" (distinct from case studies) was never built as a separate type. Difficulty is tagged per-question at generation time (`easy`/`medium`/`hard`/`mixed`) — see Quiz Engine below for why this isn't "adaptive difficulty" as a student-facing behavior.

Done: opt-in web-search grounding — `Quiz.include_web_search` (default `false`, settable on `POST /notebooks/{id}/quizzes`, `docs/API.md`'s Quiz API) runs a second, independent `TaskType.INTERNET_SEARCH` retrieval alongside the existing NotebookLM grounding, appending its result to the generation context behind a `--- Current web information ---` separator with its citations merged in (`app/workers/quiz_tasks.py`, `docs/AI_WORKFLOWS.md#3`); a search failure is swallowed the same way a NotebookLM failure is, never failing generation. Surfaced as an "Include current web results" checkbox in `QuizzesSection`.

Not built: `TaskType.TOPIC_IMAGE_SEARCH` (Wikimedia/Openverse, ADR 0010, see Internet Research below) is still not wired into quiz generation.

### Quiz Engine (Phase 3)
Done: `QuizTakingView`/`QuizReviewView` (`frontend/src/components/quiz/`) — timer, question navigation, per-question autosave (`PATCH .../attempts/{id}`, rejects past the time limit rather than auto-submitting), submission, randomized question order per attempt, and a post-grading review view with per-question feedback (`AnswerReview.tsx`).

Done behind `PERSONALIZATION_ENABLED`: **adaptive generation for new mixed quizzes.** Topic mastery selects ADR 0014's exact easy/medium/hard mix, generated difficulty tags are validated against it, and the quiz records whether adaptation was applied. Insufficient evidence preserves the normal mixed request. Existing quizzes and active attempts are never changed; this adapts generation, not question order during an attempt.

Caveat: the quiz-taking UI was never verified in a live browser (Chrome extension had no connected browser during the milestones that built/reviewed it) — type-checked and unit-tested only, not manually exercised end-to-end per `.claude/rules/testing.md`'s "UI changes are manually exercised" expectation. Vitest/RTL infrastructure is now set up (`docs/TESTING.md`) with initial coverage for `QuizTakingView` and `AnswerReview` (`frontend/src/components/quiz/*.test.tsx`), but that's not a substitute for the still-outstanding manual browser pass.

### AI Evaluation (Phase 3–4)
Done: score, explanation, and per-question AI feedback for free-text answers (`short_answer`/`long_answer`/`case_study`, one batched `TaskType.QUIZ_GRADING` call per attempt, `docs/adr/0011-quiz-evaluation-scoring-design.md`). Deterministic scoring (no AI call) for objective types. Weak-topic tagging now covers objective types too: `Question.topic` (`docs/DATABASE.md#core-tables`) is populated by the `QUIZ_GENERATION` prompt at generation time and carried onto `topic_tag` by deterministic grading (`backend/app/services/quiz_attempt_service.py`), so `weak_topics.missed_count` no longer undercounts misses concentrated in objective questions.

Done behind `PERSONALIZATION_ENABLED`: graded answers produce structured learning evidence and derived mastery; deterministic, owner-scoped recommendations provide review, quiz, or challenge actions without allowing a model to change action, priority, topic, URL, or rationale.

### AI Chat (Phase 2–4)
Ask questions, explain simply/deeply, generate examples, follow-ups, Socratic teaching, cite sources, compare documents, continue conversations.

### Internet Research (Phase 3)
Current information, recent studies, images, references, external resources, research paper search, fact verification.

Done, end-to-end (orchestrator → API → UI): `TaskType.INTERNET_SEARCH` (ADR 0012, `docs/adr/0012-internet-search-integration.md`) — Tavily primary, Brave optional fallback (only attempted when `BRAVE_SEARCH_API_KEY` is configured), Gemini synthesizes a cited answer from the normalized results (`ai/internet_search/`, `docs/AI_WORKFLOWS.md#5`), exposed via `POST /notebooks/{id}/search` (`docs/API.md`) and (now wired into quiz generation too, see Quiz Generator above). `TaskType.TOPIC_IMAGE_SEARCH` (ADR 0010) is also done end-to-end at the same shape — Wikimedia Commons primary, Openverse fallback, pure retrieval with no LLM synthesis step (`ai/image_search/`), exposed via `POST /notebooks/{id}/image-search` and a per-assistant-message "Find an image" action rendering `ImageResultCard` (visible attribution/license, per `.claude/rules/ui.md`). `TaskType.PAPER_SEARCH` (ADR 0013, `docs/adr/0013-paper-search-integration.md`) closes the research-paper gap — arXiv primary, Semantic Scholar optional fallback (only attempted when `SEMANTIC_SCHOLAR_API_KEY` is configured), same Gemini-synthesis shape as internet search (`ai/paper_search/`, `docs/AI_WORKFLOWS.md#9`). The Ask tab's search toggle is now a 3-way Notebook/Web/Papers radio group (`AskNotebookSection.tsx`); each mode renders as its own distinct chat message kind (`notebook`/`web_search`/`paper_search`) with clickable external-link citations, persisted across reload via the conversation-scoped search endpoints (`docs/API.md`).

Not built: `TaskType.TOPIC_IMAGE_SEARCH` still isn't wired into quiz generation (see Quiz Generator above).

### Overleaf Export (Phase 2+)
LaTeX notes, assignments, reports, formula sheets, tables, figures. Not started — distinct from the plain PDF export already shipped for AI Chat (client-side, from the rendered DOM, `frontend/src/lib/chat-export.ts`), which is a generic conversation export, not a LaTeX/Overleaf pipeline for generated study materials.

### Progress Tracking (Phase 3–4)
Implemented: quiz score history, deterministic topic mastery/confidence, weakness detection, notebook progress summaries, bounded study-time activity, UTC-date learning streaks, and factual revision history.

### Analytics (Phase 4)
Implemented: mastery/progress summaries, quiz-performance trends, time-spent analytics, study heatmaps, and paginated revision history in the API and dashboard. Notebook study time counts visible activity only, flushes bounded idempotent chunks, and ignores very short sessions.

### Personalization & Recommendations (Phase 4)
Implemented behind `PERSONALIZATION_ENABLED`: explicit user-scoped explanation depth/style, deterministic behavioral suggestions that remain pending until accepted, accepted-preference prompt adaptation, deterministic mastery-based recommendations, and adaptive mixed-quiz generation. No free-form learner profile or profiling-model call is stored.

### Future / Phase 5+
Voice tutor, speech recognition, AI whiteboard, diagram generator, YouTube summarizer, research assistant, coding tutor, math solver, study planner + calendar integration, mobile app, offline sync, AI debate mode, AI interview mode, AI mock exams.

<!-- TODO: add acceptance criteria per feature as each is implemented -->
