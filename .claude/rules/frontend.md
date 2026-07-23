# Frontend Rules

## Purpose
React/Vite/TypeScript conventions — applies to anything under `frontend/`.

## Responsibilities
Presentation, client-side state (TanStack Query for server state), form handling (React Hook Form). No business logic, no direct AI provider calls — always through the FastAPI backend.

## Coding Rules
- Functional components + hooks only, no class components.
- One component per file, `PascalCase.tsx` filename matching the component name.
- Props typed with an explicit `interface`/`type`, no untyped `any` props.
- Server state via TanStack Query (not `useEffect` + manual fetch); local UI state via `useState`/`useReducer`.

## Conventions
- `camelCase` variables/functions, `PascalCase` components/types, `kebab-case` for non-component files (hooks, utils).
- Tailwind utility classes for styling; shadcn/ui as the base component layer (extend via composition, `docs/UI_UX.md#component-conventions`).
- Framer Motion for animation, respecting `prefers-reduced-motion` (`docs/UI_UX.md#accessibility`).

## Best Practices
- Lift state to context/query cache instead of prop-drilling past 2 levels.
- Co-locate a component's styles/tests/types with the component.
- Loading/error states handled explicitly for every data-fetching component (TanStack Query's states).

## Avoid
- `any` without a comment justifying it.
- Direct `fetch`/`axios` calls scattered in components — go through a shared API client (`frontend/src/lib/`).
- Prop-drilling more than 2 levels.
- Inline styles where a Tailwind utility or shadcn variant exists.

## Review Checklist
- [ ] No untyped `any`.
- [ ] Server state goes through TanStack Query.
- [ ] Component handles loading/error states.
- [ ] Passes `pnpm lint`.
- [ ] Keyboard-navigable / meets `docs/UI_UX.md#accessibility` for interactive elements.
- [ ] Manually exercised in a running browser before marked done.
