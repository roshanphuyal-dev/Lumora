---
name: generate-notes
description: Generate structured study notes (notes/study guide) grounded in a Notebook's sources. Use when asked to generate notes, a study guide, or revision notes from uploaded/indexed material.
---

# Generate Notes

## Objective
Produce structured, source-grounded notes (or a broader study guide) from a Notebook's indexed Sources, following the pipeline in `docs/AI_WORKFLOWS.md#1-upload-document--notebooklm--gemini--notes`.

## Inputs
- Notebook ID (and optionally a specific Source/topic scope).
- Desired note type: detailed notes / revision notes / study guide.
- Desired depth (simple/deep) if specified by the user.

## Outputs
- Structured markdown notes with section headings matching the source material's structure.
- Citation references back to the originating Source/Chunk for each major claim (`docs/GLOSSARY.md#grounding`).

## Expected Quality
- Every non-trivial claim traceable to a cited Source.
- No content invented beyond what the sources support, unless explicitly asked to supplement with general knowledge (and then clearly labeled as such).
- Follows the `note_generation` prompt template contract (`docs/PROMPTS.md#template-index`).

## Completion Checklist
- [ ] Retrieved relevant chunks via NotebookLM/RAG before generating (not generated from the model's general knowledge alone).
- [ ] Citations present and accurate.
- [ ] Output persisted as a Generated Material (`docs/DATABASE.md`), not just returned transiently.
- [ ] Matches requested note type/depth.
