# ADR 0006: Why Oracle Cloud

## Status
Accepted

## Context
Needed a deployment target sustainable at near-zero infrastructure cost during early development/pre-revenue phases, capable of running Docker Compose (backend, frontend, Redis, Celery worker) alongside Nginx.

## Decision
Deploy on an Oracle Cloud Always Free VPS.

## Alternatives Considered
- **AWS/GCP/Azure free tiers** — typically time-limited (12 months) or resource-capped in ways that don't sustain a running product long-term without cost kicking in.
- **Railway/Render/Fly.io** — simpler deploy DX, but free tiers are usage-capped and this product's Celery workers + Redis + backend footprint would likely exceed them quickly, forcing paid tiers earlier than desired.

## Tradeoffs
Single always-free VPS has fixed, modest compute — acceptable for early-stage traffic; will need re-evaluation (new ADR) if load requires horizontal scaling or managed orchestration.

## Consequences
Deployment topology (`docs/DEPLOYMENT.md`) assumes single-VPS Docker Compose, not a multi-node/Kubernetes setup; scaling strategy is "upgrade the VPS or add ADR for multi-node" rather than auto-scaling.
