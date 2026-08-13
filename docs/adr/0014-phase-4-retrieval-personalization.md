# ADR 0014: Phase 4 Retrieval and Personalization Architecture

## Status
Accepted

## Context
ADR 0007 chose retrieval-augmented generation as the product's grounding strategy, but left the implementation choices open. Phase 4 also introduces the repository's first feature flags and the first persisted learning model beyond the historical `weak_topics` tally. Those choices affect database migrations, provider cost, tenant isolation, privacy, citations, and quiz behavior, so they must be fixed before implementation rather than inferred independently by each milestone.

The existing routing rule in `docs/AI.md` sends document-grounded work to NotebookLM first. Local retrieval should improve reliability and citation resolution without turning every grounded turn into two mandatory retrieval calls. Personalization must remain explainable and based on learning evidence, not an AI-authored psychological profile.

## Decision
Implement Phase 4 as separate, independently shippable milestones behind two new **global, environment-driven, default-off** flags: `RAG_ENABLED` and `PERSONALIZATION_ENABLED`. Phase 4 adds no per-user flag overrides.

For local retrieval:

- Use `gemini-embedding-001` through the AI orchestration layer. Request **768 output dimensions** by Matryoshka truncation of the model's native 3072-dimensional output; persist the model and dimension with each embedding. The database vector type and index are fixed at 768 dimensions rather than accepting a provider default silently.
- Preserve parser-produced PDF pages and PPTX slides as document sections. Chunk at semantic paragraph/heading boundaries, initially targeting 3,200 characters with 400-character overlap; these are evaluation-tuned parameters, not compatibility guarantees.
- Give local RAG its own document indexing lifecycle: `pending`, `indexing`, `indexed`, or `failed`. It is independent of parsing and of a `NotebookSource`'s NotebookLM indexing status.
- Run chunking and embedding asynchronously and idempotently after parsing. Backfill existing parsed documents in resumable, bounded batches with provider-429 backoff rather than dispatching an unbounded rollout wave.
- Use hybrid PostgreSQL retrieval: cosine vector search plus full-text search, merged with reciprocal-rank fusion. Every query is scoped through the requesting user's notebook sources before results may become prompt context.
- Keep **NotebookLM first** for grounded turns. Local retrieval is a supplement when it contributes distinct grounding and the full fallback when NotebookLM fails or returns no useful grounding; it is not an unconditional second provider call on every turn. If neither path grounds the answer, preserve the ungrounded fallback and label the result as ungrounded.

For citations, a local citation must refer to a source and chunk actually returned by the owner-scoped retrieval for that request. Model-produced or client-supplied identifiers are never trusted as citation authority. Citation resolution remains notebook- and owner-scoped, and carries a bounded excerpt plus page/slide locator when available. NotebookLM-native Studio artifacts remain provider-native and are not retrofitted with local chunk citations.

For learning memory and adaptive behavior:

- Persist structured evidence and derived mastery only; do not create or store free-form psychological profiles or AI-generated chat summaries as long-term memory.
- Derive notebook-scoped topic mastery from graded quiz-answer evidence using a neutral 50% prior of weight two: `mastery = (1 + sum(weight * score)) / (2 + sum(weight)) * 100`, where `weight = difficulty_multiplier * 0.5^(age_days/30)` and easy/medium-or-mixed/hard multipliers are 0.75/1.0/1.25. Confidence is `min(1, sum(weight)/5)`. Existing `weak_topics.missed_count` remains historical evidence, not the current-state decision source.
- Learning preferences are explicit and user-scoped. Deterministic behavioral signals may create only a pending suggestion; no separate profiling-model call is allowed, and a suggestion cannot affect prompts until the student accepts it.
- Recommendations are selected and prioritized deterministically. A model may rewrite batched display copy only; it cannot change the action, priority, topic, URL, or rationale.
- Adaptive quiz generation affects only newly generated quizzes and never mutates an active attempt. Mastery bands choose the difficulty mix: below 40 uses 50% easy/40% medium/10% hard; 40–69 uses 20%/60%/20%; 70 or above uses 10%/40%/50%. Insufficient evidence falls back to a normal mixed quiz and reports that adaptation was not applied.

## Alternatives Considered
- **Native 3072-dimensional embeddings** — offers the model's full output but multiplies vector storage and index cost. Rejected for Phase 4 in favor of a deliberate 768-dimensional quality/cost tradeoff that must be validated against the retrieval fixture.
- **A provider-agnostic vector dimension** — impossible at the schema boundary without separate columns/indexes or runtime incompatibility. Rejected; model/version/dimension metadata makes a future re-embedding migration explicit.
- **Always run NotebookLM and local retrieval concurrently** — maximizes redundancy but pays both latency/cost paths on every grounded turn. Rejected in favor of NotebookLM-first supplement/fallback routing.
- **Local RAG replaces NotebookLM** — loses the repository's existing multi-document knowledge-engine convention and provider-native artifacts. Rejected; local RAG complements NotebookLM.
- **Per-user rollout flags in Phase 4** — enables gradual targeting but requires a flag-assignment system that does not exist. Rejected for the first flag implementation; global default-off flags establish the minimal convention.
- **Free-form AI memory/profile summaries** — may capture nuance but introduces opaque inference, prompt-injection persistence, and sensitive profiling risk. Rejected in favor of structured, explainable learning evidence and confirmed preferences.

## Tradeoffs
Truncating embeddings may reduce retrieval quality compared with 3072 dimensions, so the fixed dimension, chunking parameters, similarity threshold, and HNSW settings must be evaluated before release. NotebookLM-first routing can add a sequential fallback delay when NotebookLM fails, while unconditional concurrency would have lower worst-case latency. Default-off global flags make rollout coarse-grained, and maintaining separate local and NotebookLM indexing lifecycles adds state and operational complexity.

The mastery formula is deliberately legible and deterministic rather than a statistically richer learner model. It can be revised through a superseding ADR after real evaluation data exists, but implementations must not silently tune it into a different behavioral contract.

## Consequences
- Milestone 1 migrations must use `vector(768)`, record embedding provenance, preserve section locators, add the separate RAG lifecycle, and document additive migration rollback as no special destructive rollback requirement.
- The initial HNSW values (`m=16`, `ef_construction=64`), chunk target/overlap, and retrieval thresholds are starting parameters to be tuned against a checked-in retrieval-evaluation fixture before release; changing the stored vector dimension requires a migration and re-embedding plan.
- Embedding document and query calls must be orchestration task types; feature and worker code must not select Gemini directly.
- Retrieval, citation resolution, mastery, preferences, and analytics queries must enforce user/notebook ownership at the database query boundary.
- Each Phase 4 milestone ships in its own branch/PR chain. This ADR may merge ahead of the implementation, and canonical docs must distinguish accepted design from shipped behavior until each milestone lands.
