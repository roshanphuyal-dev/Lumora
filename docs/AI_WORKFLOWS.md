# AI Workflows

## Purpose

Documents each concrete AI pipeline end-to-end — trigger, steps, models involved, output. `docs/AI.md` explains *why* the routing works the way it does; this doc shows *the actual sequence* for each feature.

## What Belongs Here

- One section per pipeline: trigger → steps → output.
- Which docs/rules each step depends on (linked, not repeated).

## What Never Belongs Here

- Routing rationale (`AI.md`).
- Prompt text (`PROMPTS.md`).
- Database schema for the entities involved (`DATABASE.md`).

## Structure

### 1. Upload Document → NotebookLM → Gemini → Notes
1. User uploads file → Document Processing (parse/OCR, `docs/ARCHITECTURE.md`).
2. File added as a Source to a Notebook → NotebookLM indexes it.
3. User requests "Generate Notes" → orchestrator asks NotebookLM for relevant grounded content + citations.
4. Gemini frames the retrieved content into structured notes (per `docs/PROMPTS.md` note-generation template).
5. Notes persisted (Generated Materials table, `docs/DATABASE.md`), cached for reuse.

### 2. Upload Document → Flashcards
1–2. Same as above (document indexed in Notebook).
3. NotebookLM generates flashcard-ready Q/A pairs grounded in source chunks.
4. Gemini refines phrasing/difficulty if requested (e.g. simplify, add mnemonics).
5. Flashcards persisted with source citations.

### 3. Upload Document → Quiz
1–2. Same as above.
3. Orchestrator requests relevant chunks from NotebookLM for the target topic/scope.
4. Gemini generates quiz questions (type per user selection: MCQ/true-false/short-answer/etc.) with grounded distractors.
5. Quiz + Questions persisted; difficulty tagged for adaptive selection (`docs/DATABASE.md`).

### 4. User Question → RAG → NotebookLM → Gemini (AI Chat)
1. User asks a question in a notebook-scoped chat.
2. Orchestrator embeds the question, retrieves top-k chunks from `pgvector` scoped to the notebook.
3. NotebookLM cross-references for multi-document reasoning/citation if multiple sources are relevant.
4. Gemini synthesizes an answer using retrieved context + conversation history, with citations attached.
5. Response persisted to AI Chats; contributes to memory/personalization signal if it reveals a knowledge gap.

### 5. Internet Search → Gemini
1. Query determined to need current/external information (not covered by notebook sources) — see routing step 4 in `docs/AI.md`.
2. Tavily/Brave search executed, results cached (`docs/TOKEN_OPTIMIZATION.md`).
3. Gemini synthesizes an answer citing external sources, clearly distinguished from notebook-grounded citations.

### 6. Quiz Submission → Evaluation → Progress Tracking
1. User submits quiz attempt.
2. Gemini grades (structured JSON: score, per-question correctness, explanation of mistakes).
3. Weak topics extracted and written to the student's long-term profile (`docs/AI.md#memory--personalization`).
4. Progress/Analytics tables updated (streak, mastery, accuracy trend, `docs/DATABASE.md`).
5. Personalized improvement plan/recommendations surfaced on the dashboard.

### 7. (Reserved) Study Plan Generation
<!-- TODO: document once Phase 4 adaptive study planning is implemented -->

### 8. (Reserved) Audio Overview Generation
<!-- TODO: document NotebookLM audio pipeline once implemented -->

<!-- Add new workflows above this line as features ship. Keep one numbered section per pipeline. -->
