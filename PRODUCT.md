# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + TypeScript, Tailwind CSS, shadcn/ui, React Router, TanStack Query, Framer Motion, React Hook Form (`docs/TECH_STACK.md`, `.claude/rules/frontend.md`). Backend: FastAPI + Python, SQLAlchemy, Celery + Redis, JWT auth. Data: PostgreSQL (Supabase) + pgvector, Supabase Storage. Already an established repo decision, not delegated during this init.

## Users

Students (secondary through university) and self-learners who have source material (lecture slides, textbooks, PDFs, notes) and want it turned into structured, gradable, revisable study content — grounded in *their* material, not generic web answers (`docs/PROJECT_PLAN.md#target-user`).

## Product Purpose

Turns any learning material (PDF/DOCX/PPTX/images/URLs) into personalized study resources (notes, flashcards, quizzes, study guides) and adapts to the student over time via long-term memory and knowledge retrieval. Success means a student's own uploaded material becomes usable, citable study content without manual re-authoring.

## Positioning

Grounded, citable answers from the student's own sources (NotebookLM-backed RAG), not hallucinated generic tutoring. One upload → many output formats (notes, flashcards, quizzes, mind maps, audio) without re-authoring. Adaptive difficulty and weak-topic detection that improves the more the student uses it (`docs/PROJECT_PLAN.md#core-value-proposition`).

## Operating Context

Core workflow: upload source material → material is parsed/indexed into a Notebook (multi-document knowledge base) → student generates and studies notes/flashcards/quizzes/study guides grounded in that Notebook → AI chat tutor and quiz evaluation build a per-student weak-topic/mastery history that feeds back into future generation and difficulty. Domain vocabulary (Notebook vs Document vs Source vs Chunk) is fixed in `docs/GLOSSARY.md` — don't invent synonyms.

## Capabilities and Constraints

Phase 1 (in progress, `docs/ROADMAP.md`): auth (login/register/Google login/profiles), dashboard skeleton, document upload/parsing (PDF/PPTX/DOCX/image-OCR), NotebookLM document indexing, Gemini teaching-explanation calls with OpenCode Zen fallback (ADR 0008). Phase 2+ (not started): notes/flashcards/study guides, AI chat, quiz generation/engine/evaluation, internet search, full RAG/personalization, voice/whiteboard/mobile expansion (`docs/ROADMAP.md`).

Every AI-generated answer should trace back to the student's uploaded sources when possible (RAG, citations) rather than relying on generic model knowledge (`CLAUDE.md#philosophy`).

## Brand Commitments

Product name: **Lumora**. Note: at the time of this record, `README.md` and backend/AI package names (`ai-tutor-backend`, `ai-tutor-ai` equivalents) still say "AI Tutor" — a stale-naming gap in the repo, not a second confirmed name; not corrected as part of this init (out of scope for a product-context capture).

No logo, tagline, tone-of-voice guide, or other binding brand asset exists yet. Visual identity constraints so far are limited to `docs/UI_UX.md`'s design tokens (emerald accent, zinc neutral base, Source Serif 4 for reading content + Inter for UI chrome, shadcn "new-york" style, WCAG 2.1 AA baseline, dark mode from Phase 1).

## Evidence on Hand

None yet — confirmed pre-content. No sample documents, demo notebook/quiz data, screenshots, or testimonials exist in the repo. Design and content work must use realistic placeholder content, not fabricate testimonials, benchmarks, or usage stats.

## Product Principles

- Grounded over generic: every answer/material should trace back to the student's uploaded sources when possible, not generic LLM knowledge.
- One upload, many outputs: a single source material set should produce multiple study formats without the student re-authoring anything.
- Adaptive over static: the product should get more useful to a given student the more they use it (weak-topic detection, difficulty adaptation).
- Ship incrementally per roadmap phase — don't build later-phase plumbing while earlier-phase basics are unfinished.
- Citations are a first-class UI element wherever AI-generated content appears, not a footnote (`docs/UI_UX.md`).

## Accessibility & Inclusion

WCAG 2.1 AA baseline. All interactive elements keyboard-navigable; quiz engine (timer, navigation, submission) must work without a mouse. Color never the sole carrier of semantic meaning (correct/incorrect, success/warning). Respects `prefers-reduced-motion` and `prefers-color-scheme` (`docs/UI_UX.md`).
