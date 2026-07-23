# Documentation Rules

## Purpose
Keep `docs/` and code from drifting apart as the project spans years of changes.

## Responsibilities
Every change that affects behavior described in a doc updates that doc in the same PR.

## Coding Rules
- New feature → update `docs/FEATURES.md` (and its phase in `docs/ROADMAP.md` if it completes one).
- New/changed schema → update `docs/DATABASE.md#core-tables`.
- New/changed endpoint group → update `docs/API.md`.
- New architectural or dependency decision of consequence → new ADR in `docs/adr/`, indexed in `docs/DECISIONS.md`.
- User-facing change → `CHANGELOG.md` entry under `[Unreleased]`.

## Conventions
- Each doc has one clear responsibility (see its own Purpose section) — don't duplicate content across docs; link instead.
- New domain terms that are ambiguous or overloaded get added to `docs/GLOSSARY.md`.

## Best Practices
- Prefer updating an existing doc's section over creating a new file, unless the concern genuinely doesn't fit anywhere existing.
- TODOs in docs are fine (they mark known future work) — just don't let a TODO stand in for content that's actually already decided.

## Avoid
- Copy-pasting a paragraph across two docs instead of linking.
- Letting `docs/FOLDER_STRUCTURE.md` or `docs/DATABASE.md` drift from actual code structure/schema.
- Adding a new top-level `docs/*.md` file for a concern that fits inside an existing one.

## Review Checklist
- [ ] Docs affected by this change are updated in the same PR.
- [ ] No new content duplicated from another doc (linked instead).
- [ ] New ambiguous terms added to `docs/GLOSSARY.md`.
- [ ] `CHANGELOG.md` updated if user-facing.
