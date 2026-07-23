# UI Rules

## Purpose
Enforcement checklist for `docs/UI_UX.md` — visual/interaction consistency and accessibility, applied per-PR.

## Responsibilities
Keep the UI consistent with the design tokens/component conventions, and accessible by default.

## Coding Rules
- Use shadcn/ui primitives + Tailwind utilities; no ad-hoc CSS unless no shadcn/Tailwind equivalent exists.
- Every interactive element keyboard-navigable; quiz engine controls (timer, nav, submit) work without a mouse.
- Color never the sole carrier of semantic meaning (correct/incorrect, success/warning) — pair with icon/text.

## Conventions
- Dark mode: respect `prefers-color-scheme`, support manual override, persisted per user.
- Animations respect `prefers-reduced-motion`.

## Best Practices
- Citations/source links visible as first-class UI wherever AI-generated content appears (`docs/UI_UX.md#ux-principles-product-specific`), not a footnote.
- Autosave aggressively in study/quiz flows to minimize lost work from interruption.

## Avoid
- Modal interruptions during active study/quiz sessions.
- Relying on hover-only interactions (breaks keyboard/touch users).
- Forking shadcn primitives without an ADR justifying it.

## Review Checklist
- [ ] Keyboard-navigable.
- [ ] Meets WCAG 2.1 AA contrast for new colors.
- [ ] Respects `prefers-reduced-motion`/`prefers-color-scheme`.
- [ ] Citations visible if content is AI-generated and source-grounded.
- [ ] Manually verified in a running browser (light + dark).
