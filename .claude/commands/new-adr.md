---
description: Scaffold a new ADR file from the template and add it to the DECISIONS.md index.
---

Create a new Architecture Decision Record:

1. Find the highest-numbered file in `docs/adr/` and pick the next number.
2. Copy `docs/adr/0000-template.md` to `docs/adr/00NN-<slug>.md` using a kebab-case slug from the decision title given in `$ARGUMENTS`.
3. Fill in Context/Decision/Alternatives/Tradeoffs/Consequences based on `$ARGUMENTS` and any conversation context — ask if the rationale isn't clear rather than inventing it.
4. Add a row to the index table in `docs/DECISIONS.md`, status `Proposed` unless told otherwise.
