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

Not built: internet search integration and image retrieval for quiz content (Tavily/Brave, Wikimedia/Openverse/Unsplash) — see Internet Research below, still Not Started.

### Quiz Engine (Phase 3)
Done: `QuizTakingView`/`QuizReviewView` (`frontend/src/components/quiz/`) — timer, question navigation, per-question autosave (`PATCH .../attempts/{id}`, rejects past the time limit rather than auto-submitting), submission, randomized question order per attempt, and a post-grading review view with per-question feedback (`AnswerReview.tsx`).

Not built: **adaptive question selection.** Only difficulty *tagging* exists (assigned once at quiz-generation time, static thereafter) — no logic selects/adjusts which questions a student sees based on prior performance. Deferred to Phase 4 per `docs/ROADMAP.md`'s original plan; don't read "adaptive difficulty" in the Quiz Generator feature above as this.

Caveat: the quiz-taking UI was never verified in a live browser (Chrome extension had no connected browser during the milestones that built/reviewed it) — type-checked and unit-tested only, not manually exercised end-to-end per `.claude/rules/testing.md`'s "UI changes are manually exercised" expectation. Vitest/RTL infrastructure is now set up (`docs/TESTING.md`) with initial coverage for `QuizTakingView` and `AnswerReview` (`frontend/src/components/quiz/*.test.tsx`), but that's not a substitute for the still-outstanding manual browser pass.

### AI Evaluation (Phase 3–4)
Done: score, explanation, and per-question AI feedback for free-text answers (`short_answer`/`long_answer`/`case_study`, one batched `TaskType.QUIZ_GRADING` call per attempt, `docs/adr/0011-quiz-evaluation-scoring-design.md`). Deterministic scoring (no AI call) for objective types. Weak-topic tagging now covers objective types too: `Question.topic` (`docs/DATABASE.md#core-tables`) is populated by the `QUIZ_GENERATION` prompt at generation time and carried onto `topic_tag` by deterministic grading (`backend/app/services/quiz_attempt_service.py`), so `weak_topics.missed_count` no longer undercounts misses concentrated in objective questions.

Not built: improvement plan, learning recommendations — no Phase 3/4 code surfaces these yet; Progress/Analytics tables are not updated by quiz grading either (`docs/AI_WORKFLOWS.md#6`, steps 4-5).

### AI Chat (Phase 2–4)
Ask questions, explain simply/deeply, generate examples, follow-ups, Socratic teaching, cite sources, compare documents, continue conversations.

### Internet Research (Phase 3)
Current information, recent studies, images, references, external resources, research paper search, fact verification.

### Overleaf Export (Phase 2+)
LaTeX notes, assignments, reports, formula sheets, tables, figures. Not started — distinct from the plain PDF export already shipped for AI Chat (client-side, from the rendered DOM, `frontend/src/lib/chat-export.ts`), which is a generic conversation export, not a LaTeX/Overleaf pipeline for generated study materials.

### Progress Tracking (Phase 3–4)
Daily study time, quiz scores, topic mastery, weakness detection, learning streak, revision history.

### Analytics (Phase 4)
Topic accuracy, time spent, performance graphs, improvement trends, learning heatmaps.

### Future / Phase 5+
Voice tutor, speech recognition, AI whiteboard, diagram generator, YouTube summarizer, research assistant, coding tutor, math solver, study planner + calendar integration, mobile app, offline sync, AI debate mode, AI interview mode, AI mock exams.

<!-- TODO: add acceptance criteria per feature as each is implemented -->
