# ADR 0003: Why PostgreSQL + Supabase

## Status
Accepted

## Context
Needed a relational database with native vector similarity search (for RAG embeddings) plus managed hosting, auth-adjacent features, and file storage — without standing up separate infra for each concern on a free-tier-constrained deployment target (Oracle Cloud Always Free VPS).

## Decision
Use PostgreSQL with the `pgvector` extension, hosted on Supabase (managed Postgres + Storage).

## Alternatives Considered
- **Dedicated vector DB (Pinecone/Weaviate/Qdrant)** — purpose-built for vector search, but adds a second database to keep consistent with the relational data (users, quizzes, progress); `pgvector` keeps embeddings and relational data transactionally consistent in one store.
- **Self-hosted Postgres on the Oracle VPS** — avoids a third-party dependency, but loses Supabase's managed backups/Storage/dashboard, adding ops burden to a single free-tier VPS already running the app itself.

## Tradeoffs
`pgvector` similarity search is not as fast at very large scale as specialized vector DBs — acceptable given expected per-user/per-notebook data volumes; revisit if a notebook's embedding count grows into the millions.

## Consequences
Embeddings and relational data share one database (`docs/DATABASE.md`), simplifying transactions (e.g. writing a Document + its Embeddings atomically). Supabase Storage is the default for uploaded files/generated assets.
