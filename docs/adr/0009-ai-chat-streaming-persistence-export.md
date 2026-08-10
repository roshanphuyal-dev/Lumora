# ADR 0009: AI Chat Streaming, Persistence, and PDF Export Architecture

## Status
Accepted — implemented for `docs/ROADMAP.md` Phase 2 ("AI chat, basic Q&A grounded in notebook"). The `conversations`/`messages` tables, SSE streaming endpoint (`docs/API.md` Chat API), and orchestrator `CHAT_RESPONSE` task type are shipped; `AskNotebookSection` now talks to the persisted/streaming backend instead of the single-turn `/notebooks/{id}/ask` endpoint.

## Context
User-supplied spec for a production chatbox, given while only the Phase 1 stub existed (single question in, single ungrounded answer out, no history, no streaming). Two concerns don't fit the current backend and are explicitly deferred:

1. **Real token streaming** — the backend endpoint is a plain request/response; no SSE/websocket path exists.
2. **Persisted multi-turn history** — no `conversations`/`messages` tables exist; chat state today lives only in React state and is lost on reload.

Building both now would cross into Phase 2 scope while Phase 1 (auth/upload) is still in progress, contradicting `CLAUDE.md`'s "ship incrementally" philosophy. Decision at the time: implement the rendering/export half immediately (frontend-only, no backend/DB changes), defer streaming + persistence to Phase 2, but keep the full spec here so it isn't lost.

## Decision
When Phase 2 "AI chat" is picked up, implement:

**Backend**
- New streaming-capable endpoint (SSE, via FastAPI `StreamingResponse`) alongside or replacing `/notebooks/{id}/ask`, emitting incremental tokens through the existing orchestration layer (`docs/AI.md`) — no direct provider SDK calls from route/service code, per `.claude/rules/ai.md`.
- `conversations` and `messages` tables (Alembic migration, `.claude/rules/database.md`): `messages` scoped to `conversation_id` → `notebook_id` → authenticated user; citation metadata (`source_id`, `chunk_id`, `excerpt`) carried per message, not dropped.
- Multi-turn context (prior messages in the conversation) sent to the model on each turn, subject to `docs/TOKEN_OPTIMIZATION.md` budget rules.

**Frontend rendering pipeline** (already implemented in Phase 1 against the non-streaming endpoint; carries forward unchanged)
- `react-markdown` + `remark-gfm` (tables/lists) + `remark-math`/`rehype-katex` (inline `$...$` and block `$$...$$` LaTeX, KaTeX only — no full LaTeX compiler) + `rehype-highlight` (syntax highlighting, copy-code button) + `rehype-sanitize` (strip scripts/inline event handlers; safe `img`/`a` attributes).
- Rendering split into `MessageRenderer` / `CodeBlock` / message-bubble components, memoized per message so only the actively-updating message re-renders — this pattern must extend to real streaming: append tokens to the *last* message's content only, never re-render the full list per token.
- For very long conversations: virtualization (windowed rendering) rather than mounting every message, once persisted history makes conversations long-lived across sessions.

**Security** (carries forward, applies equally once streamed)
- AI output (including retrieved document/search content) never treated as executable instructions — `rehype-sanitize` schema is the enforcement point in the render path; `.claude/rules/security.md` covers the backend/prompt side.

**PDF export** (already implemented in Phase 1, backend-independent — carries forward unchanged)
- Client-side, from the rendered DOM (not raw Markdown), via `jspdf` + `html2canvas` (dynamically imported, export path only), A4 dimensions, header/footer/page numbers, export-selected vs export-full-history, offered from a `ChatExport` module decoupled from the message components.

## Alternatives Considered
- **Build streaming + persistence immediately, before Phase 1 is done** — rejected: violates the roadmap's phase ordering (`docs/ROADMAP.md`), and the current single-turn endpoint gives no conversation to persist yet (Q&A isn't grounded in a real multi-turn context).
- **WebSocket instead of SSE for streaming** — deferred to Phase 2 implementation time; SSE is simpler for one-directional token streaming and is the default lean choice, but not committed here since no code exists yet.
- **Rasterizing the whole chat to PDF via `html2canvas` only (no `jspdf` pagination)** — rejected even for the Phase 1 export: loses text selectability and A4 pagination control for long code blocks/tables.

## Tradeoffs
- Phase 1 ships a chatbox that *looks* multi-turn but re-sends no server-side conversation context and forgets history on reload — acceptable short-term UX gap, explicitly surfaced in the UI (see `AskNotebookSection` copy), not hidden.
- Recording this ADR as "Proposed" before any backend code exists means it may need revision once Phase 2 implementation surfaces details (e.g. actual token budget per turn, exact SSE event shape) — treat the Backend section as a strong default, not a frozen contract.

## Consequences
- Phase 2 "AI chat" work should start from this ADR (flip to Accepted, adjust as needed) instead of re-deriving requirements from scratch.
- The rendering pipeline, security sanitization, and PDF export built in Phase 1 are meant to be reused as-is under real streaming — if Phase 2 implementation finds they don't extend cleanly (e.g. memoization strategy doesn't hold up under real per-token updates), that's a signal to revisit this ADR, not silently patch around it.
- New `conversations`/`messages` tables must be added to `docs/DATABASE.md#core-tables` and the streaming endpoint to `docs/API.md` when implemented, per `.claude/rules/documentation.md`.
