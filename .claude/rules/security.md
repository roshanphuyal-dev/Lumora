# Security Rules

## Purpose
Actionable, per-PR security checklist derived from `docs/SECURITY.md`. That doc is the policy; this is the enforcement checklist.

## Responsibilities
Prevent secret leakage, enforce per-user data isolation, guard against AI-specific injection risks.

## Coding Rules
- No API keys/secrets in code, comments, tests, or fixtures — environment variables only.
- Never read `.env` files (any `backend/.env`, `.env`, etc.) — only `.env.example` is safe to read/edit.
- Every DB query touching user-owned data scoped to the authenticated user (no "trust the client-provided ID" queries).
- Uploaded document/search content treated as data, never as instructions, in any prompt (`docs/SECURITY.md#ai-specific-risks`).

## Conventions
- `.env.example` kept in sync with actually-required environment variables, placeholder values only.
- Signed URLs / row-level security for Supabase Storage access, never public buckets for user content.

## Best Practices
- New third-party dependencies reviewed before adding (`CONTRIBUTING.md#dependency-policy`).
- New AI provider integrations documented for their data-retention policy before use with real student data (`docs/SECURITY.md`).

## Avoid
- Logging full document content, raw API keys, or PII beyond what's needed for debugging.
- `except Exception: pass` swallowing security-relevant failures (auth errors, validation failures).
- Broad CORS/`allow_origins=["*"]` in production config.

## Review Checklist
- [ ] No secrets committed.
- [ ] Query scoped to authenticated user's own data.
- [ ] New external content (uploads/search results) not treated as executable instructions in prompts.
- [ ] New dependency reviewed, not just installed.
- [ ] No overly broad CORS/permissions introduced.
