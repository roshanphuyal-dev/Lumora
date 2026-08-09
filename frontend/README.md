# frontend/

React + Vite + TypeScript SPA (Tailwind CSS v4, shadcn/ui, React Router, TanStack Query, Framer Motion, React Hook Form).

- Conventions: [`.claude/rules/frontend.md`](../.claude/rules/frontend.md)
- Design system: [`DESIGN.md`](../DESIGN.md), design/UX intent: [`docs/UI_UX.md`](../docs/UI_UX.md)
- Target internal layout: [`docs/FOLDER_STRUCTURE.md`](../docs/FOLDER_STRUCTURE.md#target-as-modules-are-implemented)
- API contract it consumes: [`docs/API.md`](../docs/API.md)

## Setup

```bash
pnpm install
cp .env.example .env
pnpm dev
```

## Commands

| Task | Command |
|---|---|
| Dev server | `pnpm dev` |
| Build | `pnpm build` |
| Lint | `pnpm lint` |
| Preview production build | `pnpm preview` |
