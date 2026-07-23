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
JWT bearer tokens; Google OAuth as an alternative login path. Token expiry + refresh strategy TBD at implementation. Row-level authorization: a user can only ever read/write their own courses/notebooks/documents/quizzes — enforced at the query layer, not just the API layer.

### Secrets Management
All API keys (Gemini, NotebookLM, OpenRouter, Tavily/Brave, Supabase) live in environment variables, never committed. `.env.example` documents required keys with placeholder values only. Production secrets injected via deployment environment (`docs/DEPLOYMENT.md`), never baked into Docker images.

### Data Protection
- Uploaded documents and generated study material are private to the owning user by default.
- Supabase Storage access scoped per-user (signed URLs / row-level security), not public buckets.
- No student data sent to third-party AI providers beyond what's necessary for the requested generation — no bulk export of a user's full corpus to a provider "for caching" without justification.

### AI-Specific Risks
- **Prompt injection via uploaded documents**: a malicious PDF/DOCX could contain text instructing the model to ignore prior instructions or exfiltrate data. Mitigation: treat document content as data, not instructions — system prompts must explicitly distinguish "source content" from "instructions," and generation output should be validated against expected schema before use.
- **Data leakage through model providers**: understand and document each provider's data retention policy (Gemini, OpenRouter-routed models, NotebookLM) before sending sensitive student data through them.
- **Search API results**: treat as untrusted external content, same injection caution as uploaded documents.

### Dependency & Supply Chain
Pin dependencies (`CONTRIBUTING.md#dependency-policy`); review new dependencies before adding. Dependabot/`uv`/`pnpm` audit tooling to be wired into CI (`docs/DEPLOYMENT.md`).

### Reporting
<!-- TODO: add security contact / disclosure process once this repo has external contributors -->

<!-- TODO: define token expiry/refresh policy at Phase 1 implementation -->
<!-- TODO: document each AI provider's data retention policy before Phase 1 ships -->
