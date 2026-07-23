---
name: generate-quiz
description: Generate a quiz (MCQ, true/false, fill-in-blank, matching, short/long answer, case studies) grounded in a Notebook's sources. Use when asked to generate a quiz or test questions from uploaded/indexed material.
---

# Generate Quiz

## Objective
Produce a quiz grounded in a Notebook's Sources, following `docs/AI_WORKFLOWS.md#3-upload-document--quiz` and the question types in `docs/FEATURES.md#quiz-generator-phase-3`.

## Inputs
- Notebook/topic scope.
- Question type(s) requested (MCQ/true-false/fill-in-blank/matching/assertion-reason/short/long/case-study).
- Difficulty level or adaptive-difficulty flag.
- Number of questions.

## Outputs
- JSON list of question objects matching the `quiz_generation` template schema (`docs/PROMPTS.md#template-index`), each with source citation for grounded distractors/answers.
- Persisted `Quiz`/`Question` records (`docs/DATABASE.md#core-tables`).

## Expected Quality
- Distractors plausible but unambiguously wrong given the source material.
- Difficulty tagging consistent enough to support adaptive selection later.
- No question answerable only from outside knowledge unless the notebook lacks coverage and that's explicitly acceptable.

## Completion Checklist
- [ ] Questions grounded in retrieved chunks, not invented from general knowledge.
- [ ] Correct answer + explanation present for grading (`docs/AI_WORKFLOWS.md#6-quiz-submission--evaluation--progress-tracking`).
- [ ] Persisted to `quizzes`/`questions` tables.
- [ ] Question type(s) match what was requested.
