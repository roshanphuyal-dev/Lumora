# UI/UX

## Purpose

Design and interaction reference: visual language, component conventions, accessibility, and UX principles specific to a study/tutoring product.

## What Belongs Here

- Design tokens (color, spacing, typography) and how they map to Tailwind/shadcn config.
- Accessibility standards.
- UX principles specific to this product (e.g. cognitive load management for a study tool).
- Component conventions beyond generic React/TS rules (those are in `.claude/rules/frontend.md`).

## What Never Belongs Here

- Generic React coding conventions (`.claude/rules/frontend.md`).
- Feature specs (`FEATURES.md`).

## Structure

### Design Tokens
Defined in `frontend/src/index.css` (Tailwind v4 CSS-first `@theme`/`:root` config, not a `tailwind.config.ts` — see `docs/DECISIONS.md`) — this doc references the *intent* behind them. The shipped tokens, extracted from actual code, are recorded in [`DESIGN.md`](../DESIGN.md); update that file (via `$impeccable document`), not this one, when the implementation's tokens change.
- **Color**: neutral base (`zinc`) + one accent (`emerald`, for primary actions/branding) + semantic colors for quiz feedback/progress (`green` for success, `amber` for warning, `red`/`rose` for error). Success intentionally uses a *different* green shade than the `emerald` accent — an emerald "Submit" button next to an emerald "Correct!" badge would blur the distinction between "this is clickable" and "this is feedback"; kept apart even though both read as "green" at a glance. Reinforced by `.claude/rules/ui.md`'s icon/text-pairing rule regardless.
- **Typography**: Source Serif 4 (reading-optimized, variable weight) for long-form study content (notes, study guides, flashcard backs); Inter (variable weight) for UI chrome/controls/nav. Both self-hosted via `next/font`-equivalent (Vite: `@fontsource` packages) rather than a runtime Google Fonts request, to avoid a render-blocking external call.
- **Spacing/radius**: shadcn "new-york" style (tighter, less rounded than "default") — better fit for a reading/content-dense app than the more playful "default" style. Base radius `0.5rem`.

### Dark Mode
Supported from Phase 1 — students study at all hours; respect `prefers-color-scheme` by default, with a manual override toggle (`class` strategy on `<html>`) persisted to `localStorage` and, once user profiles exist, synced as a user preference server-side.

### Accessibility
- WCAG 2.1 AA as the baseline target.
- All interactive elements keyboard-navigable; quiz engine especially (timer, navigation, submission must work without a mouse).
- Sufficient color contrast for semantic feedback colors (don't rely on color alone for correct/incorrect — pair with icon/text).
- Respect `prefers-reduced-motion` for Framer Motion animations.

### UX Principles (product-specific)
- **Minimize cognitive load during study/quiz sessions** — avoid modal interruptions, autosave aggressively (quiz engine, notes editing).
- **Make grounding visible** — citations/source links should be a first-class, always-visible UI element wherever AI-generated content appears, not a tucked-away footnote.
- **Progress should feel earned, not gamified-hollow** — streaks/stats reflect real study behavior, not engagement-bait mechanics.

### Component Conventions
shadcn/ui as the base component library — extend via composition, don't fork shadcn primitives unless there's no other option (record as ADR if forking becomes necessary).

<!-- TODO: add Storybook or equivalent component catalogue once component count grows -->
