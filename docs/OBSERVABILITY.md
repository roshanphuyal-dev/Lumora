# Observability

## Purpose

How we watch the system run in production: logging conventions, monitoring, error tracking, and cost/usage dashboards. Complements `docs/TOKEN_OPTIMIZATION.md`, which covers *reducing* cost — this doc covers *seeing* it (and every other operational signal).

## What Belongs Here

- Structured logging conventions.
- Error tracking setup and triage expectations.
- Metrics/dashboards: performance, uptime, AI cost/usage per model.
- Alerting thresholds.

## What Never Belongs Here

- Cost-reduction tactics (`TOKEN_OPTIMIZATION.md`).
- Deployment/infra topology (`DEPLOYMENT.md`) — this doc assumes the system is deployed and covers watching it, not shipping it.

## Structure

### Logging
- Structured (JSON) logs from the backend, one log line per request with: request ID, user ID (if authenticated), route, status, latency, and — for AI-routed requests — which provider/model handled it and token count.
- No PII/document content in logs beyond what's needed for debugging; never log raw API keys or full document text.
- Log levels: `ERROR` for failures needing attention, `WARNING` for degraded-but-handled (e.g. Gemini fallback to OpenRouter), `INFO` for normal request lifecycle.

### Error Tracking
- Backend/frontend exceptions captured with enough context to reproduce (request ID, user action, stack trace) — tool TBD at implementation (e.g. Sentry).
- Every `ERROR`-level log or captured exception is triaged, not silently accumulated.

### Metrics & Dashboards
- **Performance**: request latency (p50/p95/p99) per endpoint, especially AI-routed ones.
- **AI cost/usage**: tokens consumed per model per day, cost estimate per model, cache hit rate (ties back to `docs/TOKEN_OPTIMIZATION.md` tactics — this is how you verify they're working).
- **Reliability**: uptime, error rate, Celery queue depth/backlog.
- **Product**: daily active students, quiz completion rate, generation success rate (useful signal for both ops and product, tracked here since it's operational telemetry).

### Alerting
- Alert on: error rate spike, AI provider rate-limit/failure spike, Celery queue backlog beyond threshold, daily cost budget approaching limit (`docs/TOKEN_OPTIMIZATION.md#cost-monitoring-pointer`).
- Thresholds TBD once there's real traffic to baseline against.

<!-- TODO: pick concrete logging/error-tracking/metrics tooling at Phase 1 deployment -->
<!-- TODO: set real alert thresholds once a usage baseline exists -->
