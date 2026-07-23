# Project Plan

## Purpose

The single canonical statement of *what this product is* and *why it exists* — the product vision, in prose, for anyone (human or agent) who needs the full picture before diving into a specific doc.

## What Belongs Here

- Product vision and mission statement.
- Target user and core value proposition.
- High-level module list (what the product does, not how it's built).
- Links out to `docs/ROADMAP.md` (when), `docs/ARCHITECTURE.md` (how), `docs/FEATURES.md` (detailed feature spec).

## What Never Belongs Here

- Implementation detail (goes in `ARCHITECTURE.md`, `AI.md`, `DATABASE.md`, etc.).
- Timelines/phases (goes in `ROADMAP.md`).
- Individual feature specs (goes in `FEATURES.md`).

## Structure

### Vision
AI-powered personal tutor that transforms any learning material into personalized study resources, continuously adapting to the student's strengths and weaknesses via long-term memory, retrieval, and intelligent tutoring.

### Target User
Students (secondary through university) and self-learners who have source material (lecture slides, textbooks, PDFs, notes) and want it turned into structured, gradable, revisable study content — grounded in *their* material, not generic web answers.

### Core Value Proposition
- Grounded, citable answers from the student's own sources (NotebookLM-backed RAG), not hallucinated generic tutoring.
- One upload → many output formats (notes, flashcards, quizzes, mind maps, audio) without re-authoring.
- Adaptive difficulty and weak-topic detection that improves the more the student uses it.

### Module Overview
Authentication · Dashboard · Document Processing · Notebook Knowledge Base · AI Processing (RAG/orchestration) · Study Material Generator · Quiz Generator & Engine · AI Evaluation · AI Chat · Internet Research · Overleaf Export · Progress Tracking · Analytics.

Detailed feature-by-feature spec: `docs/FEATURES.md`. How these modules are built: `docs/ARCHITECTURE.md`.

### Non-Goals (for now)
Anything in Phase 5+ (`docs/ROADMAP.md`) — voice tutor, whiteboard, mobile app, AI debate/interview modes — is explicitly out of scope until earlier phases ship.

<!-- TODO: add user personas once first cohort of real users is identified -->
<!-- TODO: add success metrics (retention, quiz completion rate, weak-topic improvement) once analytics ships -->
