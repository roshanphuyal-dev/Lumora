# ADR 0004: Why NotebookLM

## Status
Accepted

## Context
Needed a knowledge-retrieval engine capable of long-context, multi-document reasoning with citation support over student-uploaded material — the "grounding" value proposition central to `docs/PROJECT_PLAN.md`.

## Decision
Use NotebookLM (via CLI/MCP Server) as the dedicated knowledge/retrieval engine, separate from the general-purpose tutoring model (Gemini).

## Alternatives Considered
- **Build RAG entirely in-house on top of Gemini alone** — more control, but re-implements multi-document reasoning, citation tracking, and long-context handling that NotebookLM already provides, for a product where the tutoring/generation layer (Gemini) is the actual differentiator worth custom-building.
- **A generic vector-search-only RAG (no NotebookLM)** — cheaper and simpler, but weaker at multi-document cross-referencing and citation fidelity than NotebookLM's purpose-built reasoning.

## Tradeoffs
Adds a second AI system to orchestrate (`docs/AI.md#ai-architecture`) and a dependency on NotebookLM's CLI/MCP interface stability/availability — mitigated by keeping NotebookLM calls isolated behind the orchestration layer so it can be swapped if needed.

## Consequences
Document indexing, citation retrieval, and several Generated Material types (study guides, mind maps, flashcards, audio overviews) route through NotebookLM before Gemini touches them (`docs/AI_WORKFLOWS.md`).
