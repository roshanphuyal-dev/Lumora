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
Defined in Tailwind config + shadcn theme (`frontend/tailwind.config.ts` once implemented) — this doc references the *intent* behind them, not a duplicate value table that will drift from the actual config.
- Color: neutral base + one accent for primary actions + semantic colors (success/warning/error) for quiz feedback and progress indicators.
- Typography: one serif/reading-optimized font for long-form study content (notes, study guides), one UI sans-serif for chrome/controls — legibility for extended reading sessions is a first-class concern here, more than in a typical dashboard app.
- Spacing/radius: shadcn defaults unless a specific product need overrides them (record as ADR if so).

### Dark Mode
Supported from Phase 1 — students study at all hours; respect `prefers-color-scheme` with a manual override toggle, persisted per user.

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

<!-- TODO: finalize color palette + typography once first design pass happens -->
<!-- TODO: add Storybook or equivalent component catalogue once component count grows -->
