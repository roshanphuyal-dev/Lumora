# Security

## Purpose

The security posture reference: auth model, secrets handling, data protection, known-risk areas specific to an AI-tutor product (prompt injection via uploaded documents, PII in study material, etc.).

## What Belongs Here

- Auth/authorization model.
- Secrets management policy.
- Data protection (student data, uploaded documents) policy.
- AI-specific risks (prompt injection, data leakage through model providers) and mitigations.

## What Never Belongs Here

- Deployment/infra hardening detail (`DEPLOYMENT.md`) — this doc covers application-level security; that one covers infra.
- General code quality — `.claude/rules/security.md` carries the actionable per-PR checklist derived from this doc.

## Structure

### Authentication & Authorization
JWT bearer tokens; Google OAuth (ID token verification) as an alternative login path. Short-lived access token (30 min default) + longer-lived refresh token (30 days default), issued as a pair on login/refresh; both expiry values are configurable via environment variables. Row-level authorization: a user can only ever read/write their own courses/notebooks/documents/quizzes — enforced at the query layer, not just the API layer.

### Secrets Management
All API keys (Gemini, NotebookLM, OpenRouter, Tavily/Brave, Supabase) live in environment variables, never committed. `.env.example` documents required keys with placeholder values only. Production secrets injected via deployment environment (`docs/DEPLOYMENT.md`), never baked into Docker images.

### Data Protection
- Uploaded documents and generated study material are private to the owning user by default.
- Supabase Storage access scoped per-user (signed URLs / row-level security), not public buckets.
- No student data sent to third-party AI providers beyond what's necessary for the requested generation — no bulk export of a user's full corpus to a provider "for caching" without justification.

### AI-Specific Risks
- **Prompt injection via uploaded documents**: a malicious PDF/DOCX could contain text instructing the model to ignore prior instructions or exfiltrate data. Mitigation: treat document content as data, not instructions — system prompts must explicitly distinguish "source content" from "instructions," and generation output should be validated against expected schema before use.
- **Data leakage through model providers**: understand and document each provider's data retention policy (Gemini, OpenRouter-routed models, NotebookLM) before sending sensitive student data through them.
- **Search API results**: treat as untrusted external content, same injection caution as uploaded documents — applies to `TaskType.INTERNET_SEARCH`'s Tavily/Brave results before they reach Gemini's synthesis pass (`docs/AI.md`).

### Third-Party Provider Data Retention
Student-derived query text (a search query or study topic) leaves the system to each of these providers. Full sourcing for the two search providers is in `docs/adr/0012-internet-search-integration.md`'s Decision section; this is the retention/privacy summary, not a duplicate of the pricing/latency detail there.

- **Tavily** (`TaskType.INTERNET_SEARCH`, primary): **unresolved ambiguity, open item.** Its FAQ claims "zero data retention" and SOC 2 certification, but its actual privacy policy (updated 2025-11-24) says the opposite in substance — it collects query data, may use portions to improve future responses unless the contract says otherwise, may forward queries to third-party index providers in limited cases, and has no concrete query-specific deletion period (purpose-based retention only). **This is a hard pre-production gate** (ADR 0012's Consequences): written clarification or a DPA from Tavily is required before sending real student-derived queries, not just before "Phase 1" or any other phase boundary. Until resolved, treat Tavily query text as retained indefinitely for an unspecified purpose. Given that, query minimization is enforced at the call site: only the bare query string and search parameters ever reach Tavily — no notebook content, user identifiers, or conversation history (enforced by `backend/tests/test_tavily_client.py`'s request-body key-set assertion).
- **Brave** (`TaskType.INTERNET_SEARCH`, optional fallback): retains API query records up to 90 days for billing/troubleshooting/abuse-prevention/legal reasons. States it doesn't collect end-user identifiers connecting a query to a person and argues API query data isn't "personal data" under GDPR on that basis — but Lumora can still associate a search with a user/conversation on its own side (the request is authenticated), so Lumora remains responsible for notice/minimization/lawful-basis/deletion regardless of Brave's position. True zero-data-retention is Enterprise-only, not the default plan used here.
- **arXiv** (`TaskType.PAPER_SEARCH`, primary): keyless, publicly-run nonprofit API (`docs/adr/0013-paper-search-integration.md`). arXiv explicitly permits storing/transforming/sharing descriptive metadata (titles, abstracts, authors, identifiers) and recommends caching repeated queries rather than re-querying more than once/day — no PDFs or source files are stored or proxied, only metadata + outbound PDF URLs. Query minimization applies here too: only the bare query string reaches arXiv's `export.arxiv.org/api/query`, no notebook content or user identifiers.
- **Semantic Scholar** (`TaskType.PAPER_SEARCH`, optional fallback): **unresolved license gate, open item, structurally identical to Tavily's gate above** (ADR 0013's Consequences). Its default API license grants use for "internal use for legitimate research or educational purposes" only; commercial use (this product) requires an expanded license from Semantic Scholar/AI2, not yet obtained. Query privacy/retention (logging, retention period) is unstated in Semantic Scholar's official materials — unverified either way. **This is a hard pre-production gate**: written clarification or an expanded license from Semantic Scholar/AI2 is required before sending real student-derived queries. Until resolved, results are never persistently cached (no published cache-TTL/no-cache rule, and the license's public-display/commercial-use conditions make persistence a legal question) and `SEMANTIC_SCHOLAR_API_KEY` stays unset in production. Query minimization is enforced the same way as Tavily/arXiv: only the bare query string reaches Semantic Scholar's `paper/search` endpoint.
- **Wikimedia Commons** (`TaskType.TOPIC_IMAGE_SEARCH`, primary): keyless, publicly-run nonprofit API. No Lumora-specific data processing agreement exists; retention specifics for search-query server logs haven't been independently verified against Wikimedia's own privacy policy for this integration. <!-- TODO: confirm Wikimedia's query-log retention window before this is used with real student data at production scale, per ADR 0010's "document the provider's data-retention posture before shipping" callout -->
- **Openverse** (`TaskType.TOPIC_IMAGE_SEARCH`, fallback): anonymous/keyless by default; an optional `OPENVERSE_CLIENT_ID`/`OPENVERSE_CLIENT_SECRET` OAuth2 app only raises the rate limit, it doesn't change what's sent (still just the search query). Retention specifics likewise not independently verified. <!-- TODO: same gate as Wikimedia above -->

Neither Wikimedia nor Openverse queries are cached beyond this app's own 24h Redis cache (`ai/image_search/cache.py`); no provider-side caching claim is being made for them.

### Dependency & Supply Chain
Pin dependencies (`CONTRIBUTING.md#dependency-policy`); review new dependencies before adding. Dependabot/`uv`/`pnpm` audit tooling to be wired into CI (`docs/DEPLOYMENT.md`).

### Reporting
<!-- TODO: add security contact / disclosure process once this repo has external contributors -->

<!-- TODO: document Gemini/OpenCode Zen/NotebookLM/OpenRouter's own data retention policies (only the newer Tavily/Brave/Wikimedia/Openverse integrations are covered above) -->
