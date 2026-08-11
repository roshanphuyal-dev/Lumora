# ADR 0010: Topic-Relevant Image Retrieval

## Status
Accepted — targets `docs/ROADMAP.md` Phase 3 ("Image retrieval: Wikimedia/Openverse/Unsplash"). Requested during Phase 1/2 chatbox UI work; deferred rather than built at the time, to keep Phase 1/2 focus intact, and is now being implemented as specified here.

## Context
While building the notebook chatbox, the ask was for a way to pull a real, topic-relevant image into an Ask answer (e.g. a diagram of the simplex method) instead of relying on the model to reference or fabricate one in Markdown. This is precisely the roadmap's Phase 3 "Image retrieval" line item, not a chatbox detail — building it now would cross phase boundaries the same way ADR 0009 flagged for chat streaming/persistence.

Two things need deciding before implementation: which provider, and where it plugs into the existing chat/AI architecture.

## Decision
When Phase 3 "Image retrieval" is picked up:

**Provider**: default to **Wikimedia Commons** (`commons.wikimedia.org/w/api.php`) as primary, **Openverse** (`api.openverse.org`) as fallback — both free, keyless or low-friction-key, no billing setup, and already named in `docs/ROADMAP.md`. Do **not** default to the Google Custom Search JSON API: it requires a billing-enabled Google Cloud project and a paid tier past a small daily free quota, which doesn't fit a "pull an image" feature invoked per chat message. If a literal Google Images result set is later required as a product decision (not just "a real, relevant image"), that's a separate ADR revision, not an assumption baked in here.

**Architecture** (mirrors the existing NotebookLM/Gemini/OpenCode Zen shape in `ai/`):
- New `ai/image_search/client.py` — the only place the Wikimedia/Openverse HTTP calls happen (`.claude/rules/ai.md`: provider SDK/API calls isolated under `ai/`, nothing outside it calls the API directly).
- New `TaskType.TOPIC_IMAGE_SEARCH` in the orchestrator (`ai/orchestrator/`), taking a query string (the topic/question, not the full answer text) and returning `{ image_url, attribution, license, source_url }` — attribution and license are not optional fields: both Wikimedia Commons and Openverse content carry CC-family licenses that require attribution display in the UI wherever the image is shown, per each provider's terms.
- Frontend: a per-message "Find an image" action (button) in `ChatMessage`/`MessageRenderer`'s tooling row, calling a new `POST /notebooks/{id}/image-search`-style endpoint (exact path TBD at implementation time) with the relevant question/topic text, rendering the result inline with a visible attribution line/link — not just a bare `<img>`.

**Security/privacy**: the search query (a student's study topic) leaves the system to a third-party provider — same category of consideration as any external AI call under `docs/SECURITY.md#ai-specific-risks`, even though no model inference happens; document the provider's data-retention posture before shipping, matching the bar already set for OpenCode Zen (ADR 0008).

**Caching**: cache by normalized query text (`docs/TOKEN_OPTIMIZATION.md`'s caching principle applies here too, even though this isn't a token-costed call) — the same topic will be searched repeatedly across students/sessions.

## Alternatives Considered
- **AI image generation** (e.g. Gemini/Imagen, DALL-E) — explicitly rejected by the original ask itself: for factual study material (diagrams, historical photos, real objects), a real retrieved image is more trustworthy than a generated one, and generation adds its own cost-per-call and hallucination-risk surface that retrieval doesn't have.
- **Google Custom Search JSON API as default** — rejected as the default per above (billing/quota friction); left open as a possible additional provider behind the same `ai/image_search/` interface if a future decision explicitly wants Google's specific index.
- **Client-side-only fetch direct to the provider (no backend/orchestrator involvement)** — rejected: violates `.claude/rules/ai.md`'s "nothing outside `ai/` calls a provider directly" even for non-LLM providers, and skips server-side caching.

## Tradeoffs
- Wikimedia/Openverse's coverage is real-world-photo/diagram-oriented, not guaranteed to have a good result for every conceivable study topic (e.g. very niche or newly-coined terms) — a "no good match found" empty state is a real UI case to design for, not an edge case to ignore.
- Attribution requirements add UI surface (license text/link per image) that a naive "just show an image" implementation would skip — called out here specifically so it isn't dropped at implementation time.

## Consequences
- Phase 3 implementation should start from this ADR (flip to Accepted, adjust provider choice only via a revision, not silently) rather than re-deciding provider/architecture from scratch.
- New `ai/image_search/` module and orchestrator task type must be added to `docs/AI.md`'s routing table and `docs/API.md` when implemented, per `.claude/rules/documentation.md`.
