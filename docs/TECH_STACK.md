# Tech Stack

## Purpose

The single reference for *what* technology is used *where*, and at what version once pinned. If you're wondering "what do we use for X," check here before introducing an alternative.

## What Belongs Here

- Concrete technology choices per layer.
- Minimum version requirements.

## What Never Belongs Here

- *Why* a technology was chosen over alternatives — that's `docs/DECISIONS.md`/`docs/adr/`.
- Setup instructions — `README.md`/`CONTRIBUTING.md`.

## Structure

### Frontend
React (Vite), TypeScript, Tailwind CSS, shadcn/ui, React Router, TanStack Query, Framer Motion, React Hook Form. Package manager: **pnpm**.

### Backend
FastAPI, Python 3.12+, SQLAlchemy, Celery (background tasks), Redis, JWT authentication. Dependency/env manager: **uv**.

### Database
PostgreSQL (Supabase), `pgvector` for embeddings.

### Storage
Supabase Storage.

### AI Layer
- Primary tutor: Gemini 2.5 Flash
- Secondary/fallback: OpenRouter (DeepSeek, Qwen)
- Knowledge engine: NotebookLM CLI / MCP Server
- Embeddings: Gemini Embeddings, Jina Embeddings

### Document Processing
PyMuPDF, python-docx, python-pptx, Tesseract (OCR).

### Internet Search
Tavily, Brave Search.

### Image Sources
Wikimedia Commons, Openverse, Unsplash.

### Charts
Chart.js.

### Deployment
Oracle Cloud (Always Free VPS), Docker, Nginx, GitHub Actions.

<!-- TODO: pin exact versions once Phase 1 dependencies are locked -->
