---
name: Lumora
description: Grounded AI study tutor — an honest, task-first workspace, not a stats dashboard dressed up before it has real numbers.
colors:
  signal-emerald: "oklch(0.596 0.145 163.225)"
  signal-emerald-dark: "oklch(0.696 0.17 162.48)"
  paper: "oklch(1 0 0)"
  ink: "oklch(0.145 0 0)"
  hairline: "oklch(0.922 0 0)"
  quiet-gray: "oklch(0.556 0 0)"
  confirmed-green: "oklch(0.627 0.194 149.214)"
  caution-amber: "oklch(0.769 0.188 70.08)"
  alert-red: "oklch(0.577 0.245 27.325)"
typography:
  display:
    fontFamily: "'Source Serif 4 Variable', ui-serif, serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  body:
    fontFamily: "'Inter Variable', ui-sans-serif, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  sm: "0.3rem"
  md: "0.4rem"
  lg: "0.5rem"
  xl: "0.7rem"
spacing:
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
components:
  button-primary:
    backgroundColor: "{colors.signal-emerald}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    padding: "0.5rem 1rem"
  button-primary-hover:
    backgroundColor: "{colors.signal-emerald}"
---

# Design System: Lumora

## Overview

**Creative North Star: "The Honest Ledger"**

Lumora's Phase 1 surface is a study tool that can currently do one real thing — take a source in and open a notebook — so the design says exactly that and nothing more. The shell is a plain sidebar-and-canvas app frame, the kind a student already knows how to use without being taught. One emerald accent marks the single action that matters; everything else stays zinc-neutral so the accent never has to compete with itself. Long-form or heading content reads in a serif built for sustained reading (Source Serif 4); the chrome around it — nav, labels, buttons — stays in a plain, fast-reading sans (Inter). Nothing on the page pretends the product has usage history it doesn't have yet: sections it can't back with real data (weak topics, learning progress, streaks) are named plainly in a quiet, bordered ledger, not dressed as stat cards with invented numbers.

Confirmed visual rejection: a grid of identical icon-plus-heading-plus-text cards standing in for not-yet-built features. The first build of this dashboard shipped exactly that for its "Coming soon" section and it read as filler; the fix — a single bordered list, one row per item — is now the standard for any inert/placeholder content on this project, not a one-off.

**Key Characteristics:**
- One accent (emerald), used only on the primary action and active nav state — never decorative.
- Serif for reading/heading content, sans for everything operational.
- Flat surfaces: a single 1px ring for containment, never a drop shadow.
- Honest about what's real: empty states and "not yet available" states are first-class, not disguised.

## Colors

Restrained strategy: a zinc neutral base carries the page, one emerald accent marks the primary action, semantic colors are reserved for future quiz/feedback states and deliberately not the same hue as the accent.

### Primary
- **Signal Emerald** (`oklch(0.596 0.145 163.225)`, light mode / `oklch(0.696 0.17 162.48)` dark mode): the primary action only — the upload button and the active sidebar nav item. Nothing else on the page uses it, so it never has to share attention with itself.

### Neutral
- **Paper** (`oklch(1 0 0)`): page and card background, light mode.
- **Ink** (`oklch(0.145 0 0)`): body text, light mode.
- **Hairline** (`oklch(0.922 0 0)`): borders, dividers, the sidebar's edge.
- **Quiet Gray** (`oklch(0.556 0 0)`): secondary text — subtitles, empty-state copy, disabled nav labels.

### Named Rules
**The One Accent Rule.** Signal Emerald appears on exactly one interactive element per view (the primary action) plus the active nav state. It is never used for card backgrounds, section headers, or decoration — its rarity is what makes it read as "do this."

**The Undistinguished Green Rule.** Confirmed Green (`oklch(0.627 0.194 149.214)`) marks real "succeeded" states only (a notebook source's `indexed` status; later, quiz/evaluation "correct" feedback) and must stay a visibly different hue from Signal Emerald — a success badge sitting next to a primary button must never look like the same color choice twice.

## Typography

**Display Font:** Source Serif 4 Variable (with ui-serif, serif fallback)
**Body Font:** Inter Variable (with ui-sans-serif, sans-serif fallback)

**Character:** A reading-optimized serif for anything the student is meant to read closely (page titles, and — as the product grows — notes and study-guide content), paired with a fast, neutral sans for every operational surface (nav, buttons, labels, empty states). The pairing exists to separate "content to read" from "interface to operate," not for decoration.

### Hierarchy
- **Display** (600, 1.5rem/24px, 1.3 line-height, Source Serif 4): page-level heading only (e.g. "Welcome to Lumora"). Used once per view.
- **Body** (400, 0.875rem/14px, 1.5 line-height, Inter): all UI copy, empty-state text, nav labels.
- **Label** (500, 0.75rem/12px, Inter): section headings ("Your notebooks", "Coming soon") and the uppercase-tracked "Soon" badge (10px, uppercase, tracked wide).

### Named Rules
**The Read vs. Operate Rule.** If it's prose the student is meant to read, it's Source Serif 4. If it's an instruction to the interface (a button, a label, a nav item), it's Inter. A component never mixes the two roles.

## Layout

Sidebar-and-canvas app shell. A fixed 240px (`w-60`) left sidebar on `md` and above; below `md` the sidebar collapses entirely to a wordmark-only top bar (there is currently only one live route, so a nav drawer has nothing behind it worth building yet — revisit once Notebooks/Settings ship). The canvas is a single centered column, `max-w-4xl`, `gap-8` between major sections, generous vertical padding (`py-10`). No responsive grid reflow beyond the sidebar collapse — the content column is already single-file at every width.

## Elevation & Depth

Flat. No `box-shadow` anywhere in the system. Containment is a single `1px` ring (`ring-foreground/10`) per surface — never a ring plus a shadow together.

### Named Rules
**The Declare-Once Rule.** A surface gets exactly one containment treatment: a hairline ring. Never a border stacked under a soft shadow (the "ghost card" — rejected on sight).

## Shapes

Rounded, not sharp: base radius `0.5rem` (8px), scaling to `0.7rem` (11.2px) for cards (`rounded-xl`) and `0.3–0.4rem` for small controls and badges. No sharp corners, no pill-shaped containers except small status badges ("Soon").

## Components

### Buttons
- **Shape:** `0.4rem` radius (`rounded-md`).
- **Primary:** Signal Emerald background, Paper text, `0.5rem 1rem` padding. Used for exactly one action per view.
- **Hover / Focus:** background darkens slightly; focus-visible gets a ring in the accent color.
- **Multi-step async action (e.g. upload):** the button's own label swaps to a present-participle stage name ("Uploading…", "Reading your file…") and the button disables — never a separate spinner element or progress bar. A failure renders as `text-destructive` copy below the button plus a text "Try again" link that resets the action, never a toast/modal (`.claude/rules/ui.md`: no modal interruptions).

### Cards / Containers
- **Corner Style:** `0.7rem` (`rounded-xl`).
- **Background:** Paper (light) / near-black (dark).
- **Shadow Strategy:** none — see Elevation & Depth.
- **Border:** 1px ring, `foreground/10`.
- **Internal Padding:** `1rem` (`--card-spacing`).

### Navigation (Sidebar)
- **Style:** icon (16px, Lucide, single stroke weight) + label, Inter 14px medium.
- **Active state:** Signal Emerald text on a 10%-opacity emerald background, rounded `0.4rem`. Uses React Router `NavLink`'s `end` prop on the root route (`/`) only — without it, every route would match `/` as a prefix and Dashboard would read active everywhere.
- **Disabled state (not-yet-built routes):** Quiet Gray text at reduced opacity, plus a small uppercase "Soon" badge — never hidden entirely, so the product's near-term shape stays visible. Only "Settings" is still in this state; "Notebooks" is a real route.
- **Mobile:** sidebar hidden below `md`; replaced by a top bar with the wordmark plus each *real* route as an icon-only link (no drawer, no hidden routes — a route not worth an icon isn't shown at all on mobile rather than tucked behind a menu).

### Ledger Row (signature component)
A single bordered container, one row per item, rows divided by 1px hairline separators — never separate same-size cards. Originated as the fix for "not yet available" content (icon + label + "Soon" badge — see Overview), but the same structure is now the general list pattern project-wide: real populated lists (notebooks, sources) use it too (icon + label + a trailing date/status instead of "Soon"), sharing one component (`NotebookList`) between the dashboard's compact view and the full `/notebooks` list page rather than duplicating the states.

### Destructive Actions
No modal confirmation dialogs (`.claude/rules/ui.md`). A destructive action (delete notebook) is a two-step inline confirm: the button's own label/position becomes "Delete this notebook?" plus a `destructive`-variant "Confirm" and a plain-text "Cancel", collapsing back on cancel. A less destructive, easily-reversible action (removing one source from a notebook) skips the confirm step entirely — a small `X` icon button, immediate.

### Answer Content (Markdown)
AI-generated answers (`AskNotebookSection.tsx`) render as real Markdown (`react-markdown`), not raw text — headings, bold, lists, and tables need actual formatting to be readable, and shipping the literal `**`/`##`/`|` syntax to the page is a defect, not an acceptable simplification.

### Auth Layout
Unauthenticated routes (`/login`, `/register`) do not inherit the sidebar shell — there is nothing to navigate to yet. A single centered column (`max-w-sm`), wordmark above the form, no imagery: the same Restrained-strategy discipline as the dashboard, not a Persuade-mode marketing split. Errors render as `text-destructive` copy above the submit button, never a toast or modal (`.claude/rules/ui.md`: no modal interruptions).

## Do's and Don'ts

### Do:
- **Do** use Signal Emerald on exactly one primary action per view, plus the active nav state — nowhere else.
- **Do** render not-yet-available features as a single bordered ledger (icon + label + "Soon" per row), never as a grid of identical cards.
- **Do** self-host Source Serif 4 and Inter via `@fontsource-variable` — never fall back to a system font as the display face.
- **Do** keep Confirmed Green (success states: indexed sources, future quiz feedback) visually distinct from Signal Emerald.
- **Do** render AI-generated answer content as real Markdown, not raw text.
- **Do** confirm a destructive action with an inline two-step control, never a modal.

### Don't:
- **Don't** stack a border and a shadow on the same surface — one containment treatment per element.
- **Don't** invent numbers, streaks, or progress data before the backend can back them — an honest "Soon" label beats a fabricated stat.
- **Don't** put a low-stakes, reversible action (removing one source) behind the same confirm step as a destructive one (deleting a notebook) — match the friction to the actual cost of a mistake.
- **Don't** use icon-plus-heading-plus-text cards as a page scaffold for a set of same-weight items — that's the rejected pattern this system exists to avoid repeating.
