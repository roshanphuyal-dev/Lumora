# ADR 0002: Why React

## Status
Accepted

## Context
Needed a frontend framework with a mature component ecosystem (shadcn/ui, Framer Motion, TanStack Query), strong TypeScript support, and a large enough talent/tooling pool to keep the project maintainable over years.

## Decision
Use React with Vite as the build tool.

## Alternatives Considered
- **Vue** — strong DX, but shadcn/ui and the broader "modern AI-app" component ecosystem this project leans on skews React-first.
- **Svelte/SvelteKit** — excellent performance/bundle size, but smaller ecosystem for the specific shadcn/ui + Radix-based component patterns this project wants.
- **Next.js** (over plain Vite+React) — considered, but this product's backend is a separate FastAPI service, not Next's API routes; Next's SSR/RSC model adds complexity this project doesn't need since it's a client-rendered SPA talking to an independent API.

## Tradeoffs
Client-side-rendered SPA (via Vite) means no built-in SSR — acceptable since this is an authenticated, logged-in-first product where SEO/first-paint-for-anonymous-users isn't a priority.

## Consequences
Frontend is a pure SPA calling the FastAPI backend over REST (`docs/API.md`); no server components/SSR concerns to design around; routing handled client-side via React Router.
