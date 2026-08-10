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
Done: Notes (detailed/revision) and study guides, flashcards (Gemini-authored, grounded via NotebookLM retrieval), mind maps, infographics, slide decks, reports, audio summaries, and data tables (NotebookLM Studio-authored — see `docs/AI.md`/`docs/API.md`'s Studio API).

Not started: cheat sheets, formula sheets, mnemonics/memory tricks, timelines, comparison charts — none of these map to a NotebookLM Studio artifact type, so they'd need a dedicated Gemini-based pipeline (like Notes/Flashcards) if picked up.

### Quiz Generator (Phase 3)
MCQ, true/false, fill-in-blank, matching, assertion/reason, short answer, long answer, case studies, scenario questions, adaptive difficulty.

### Quiz Engine (Phase 3)
Timer, navigation, autosave, review answers, submission, randomization, adaptive question selection.

### AI Evaluation (Phase 3–4)
Score, explanation, mistakes, personalized feedback, weak areas, improvement plan, learning recommendations.

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
