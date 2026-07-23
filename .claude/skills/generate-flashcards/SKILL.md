---
name: generate-flashcards
description: Generate flashcards (front/back Q&A pairs) grounded in a Notebook's sources. Use when asked to generate flashcards from uploaded/indexed material.
---

# Generate Flashcards

## Objective
Produce a flashcard set grounded in a Notebook's Sources, per `docs/AI_WORKFLOWS.md#2-upload-document--flashcards`.

## Inputs
- Notebook/topic scope.
- Desired count/density.
- Style preference if given (e.g. include mnemonics/memory tricks).

## Outputs
- JSON list `{front, back, source_citation}` matching the `flashcard_generation` template (`docs/PROMPTS.md#template-index`).
- Persisted `Flashcards` records (`docs/DATABASE.md#core-tables`).

## Expected Quality
- One clear concept per card — no compound questions on a single card.
- Back side concise, front side unambiguous without the back.
- Citation present on every card.

## Completion Checklist
- [ ] Generated from retrieved NotebookLM-grounded chunks, not general knowledge.
- [ ] Each card has a source citation.
- [ ] No duplicate/near-duplicate cards in the set.
- [ ] Persisted as Generated Material.
