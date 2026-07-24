# Graph Report - Lumora  (2026-07-24)

## Corpus Check
- 147 files · ~30,772 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 822 nodes · 1661 edges · 58 communities (51 shown, 7 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 198 edges (avg confidence: 0.73)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f7c8e2c7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Auth Backend
- Claude Agents
- Content-Gen Skills & ADRs
- Repo Rules & Skills
- Module READMEs & Features
- Backend Config & Migrations Setup
- DB Migration & Core API
- Courses Backend
- AI Model Routing
- API Reference
- RAG & Glossary
- Auth Tests
- Architecture & ADR Index
- Courses Tests
- Quiz & Memory
- RAG Chat Workflow
- Supabase Storage
- Project Root
- test_orchestrator.py
- LocalFileStorage
- Tech Stack
- conftest.py
- ParsedDocument
- NotebookSourceIndexStatus
- test_parsers.py
- upload_document
- CLAUDE.md
- test_notebooks.py
- test_documents.py
- Deployment
- Architecture Overview
- update_me
- _create_document
- ADR 0001: Why FastAPI
- ADR 0004: Why NotebookLM
- ADR 0005: Why Gemini
- ADR 0007: Why RAG
- Template Index
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- celery_app.py

## God Nodes (most connected - your core abstractions)
1. `Database Schema Reference` - 32 edges
2. `API Contract Reference` - 26 edges
3. `NotebookLMClient` - 24 edges
4. `OrchestrationError` - 24 edges
5. `Features Catalogue` - 24 edges
6. `run_task()` - 23 edges
7. `AI Tutor Project README` - 23 edges
8. `Document` - 20 edges
9. `NotebookLMError` - 19 edges
10. `Token & Cost Optimization` - 19 edges

## Surprising Connections (you probably didn't know these)
- `Frontend Component` --conceptually_related_to--> `frontend/ Module README`  [INFERRED]
  docs/ARCHITECTURE.md → frontend/README.md
- `Product Roadmap (Phases 1-5)` --conceptually_related_to--> `Features Catalogue`  [INFERRED]
  README.md → docs/FEATURES.md
- `Backend (FastAPI) Component` --conceptually_related_to--> `backend/ Module README`  [INFERRED]
  docs/ARCHITECTURE.md → backend/README.md
- `Background Processing` --semantically_similar_to--> `AI Workflows`  [INFERRED] [semantically similar]
  docs/ARCHITECTURE.md → docs/AI_WORKFLOWS.md
- `test_teaching_explanation_rejects_mismatched_request_type()` --indirect_call--> `GeminiClient`  [INFERRED]
  backend/tests/test_orchestrator.py → ai/gemini/client.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Feature Implementation Handoff Pipeline (planner to architect to domain agents)** — _claude_agents_planner_planner_agent, _claude_agents_architect_architect_agent, _claude_agents_backend_backend_agent, _claude_agents_frontend_frontend_agent, _claude_agents_database_database_agent, _claude_agents_ai_ai_agent [INFERRED 0.85]
- **Pre-Merge Review, Security, and Test Quality Gate Agents** — _claude_agents_reviewer_reviewer_agent, _claude_agents_security_security_agent, _claude_agents_tester_tester_agent [INFERRED 0.85]
- **Docs-Code Synchronization Enforcement** — _claude_agents_documentation_documentation_agent, _claude_agents_architect_architect_agent, _claude_rules_documentation_documentation_rules [INFERRED 0.75]
- **PR Review Checklist Spans All Domain Rule Files** — _claude_skills_review_pr_skill, _claude_rules_frontend, _claude_rules_security, _claude_rules_testing, _claude_rules_ui, _claude_rules_git [EXTRACTED 1.00]
- **RAG-Grounded Generation Pattern (Flashcards/Notes/Quiz)** — _claude_skills_generate_flashcards_skill, _claude_skills_generate_notes_skill, _claude_skills_generate_quiz_skill [INFERRED 0.85]
- **Commit & PR Convention Defined Across Docs** — agents, claude, contributing, _claude_rules_git [INFERRED 0.85]
- **RAG Retrieval Pipeline (Chunk -> Embedding -> Retrieval -> Chat)** — docs_ai_rag_design, docs_database_embeddings, docs_ai_workflows_rag_chat, docs_glossary_chunk [INFERRED 0.80]
- **AI Orchestration Layer Routing Among Providers** — docs_ai_orchestration_layer, docs_ai_gemini, docs_ai_notebooklm, docs_ai_deepseek_qwen, docs_ai_openrouter [EXTRACTED 1.00]
- **Single-VPS Deployment Infra Stack** — docs_deployment_infra_topology, docker_docker_compose_postgres_service, docs_architecture_celery_redis, docs_architecture_postgres_pgvector [INFERRED 0.80]
- **Grounded, Citation-First RAG Design Pattern** — docs_adr_0007_rag, docs_project_plan_core_value_proposition, docs_token_optimization_request_optimization, docs_ui_ux_ux_principles [INFERRED 0.85]
- **Tiered AI Model Routing for Cost Control** — docs_tech_stack_ai_layer, docs_token_optimization_model_optimization, docs_prompts_formatting_pass, docs_adr_0005_gemini [INFERRED 0.80]
- **Definition of Done Convention Across Docs** — docs_workflow_definition_of_done, docs_roadmap_definition_of_done, docs_testing, docs_testing_coverage_expectations [INFERRED 0.75]

## Communities (58 total, 7 thin omitted)

### Community 0 - "Auth Backend"
Cohesion: 0.07
Nodes (47): do_run_migrations(), get_url(), run_migrations_offline(), run_migrations_online(), login(), login_google(), DbSession, refresh() (+39 more)

### Community 1 - "Claude Agents"
Cohesion: 0.07
Nodes (53): AI Agent, Architect Agent, Backend Agent, Database Agent, DevOps Agent, Documentation Agent, Frontend Agent, Planner Agent (+45 more)

### Community 2 - "Content-Gen Skills & ADRs"
Cohesion: 0.11
Nodes (28): Generate Flashcards Skill, Generate Notes Skill, Generate Quiz Skill, Optimize Prompt Skill, Gemini 2.5 Flash, NotebookLM, ADR Template, AI System Handbook (+20 more)

### Community 3 - "Repo Rules & Skills"
Cohesion: 0.18
Nodes (16): Git Rules, Security Rules, Testing Rules, Refactor Module Skill, Review PR Skill, Roadmap Definition of Done (per phase), Testing, Backend Testing (+8 more)

### Community 4 - "Module READMEs & Features"
Cohesion: 0.09
Nodes (35): ai/ Module README, backend/ Module README, database/ Module README, docker/ Module README, Features Catalogue, AI Chat (Feature), AI Evaluation (Feature), Analytics (Feature) (+27 more)

### Community 5 - "Backend Config & Migrations Setup"
Cohesion: 0.08
Nodes (54): Base, get_db(), AsyncSession, TimestampMixin, UUIDPrimaryKeyMixin, Course, Subject, Document (+46 more)

### Community 6 - "DB Migration & Core API"
Cohesion: 0.17
Nodes (17): Generate Database Migration Skill, Alembic, Postgres Service (docker-compose.yml), Document API, Notebook API, Auth Flow, PostgreSQL + pgvector, Database Schema Reference (+9 more)

### Community 7 - "Courses Backend"
Cohesion: 0.31
Nodes (14): create_course(), create_subject(), delete_course(), list_courses(), list_subjects(), CurrentUser, DbSession, UUID (+6 more)

### Community 8 - "AI Model Routing"
Cohesion: 0.18
Nodes (16): DeepSeek/Qwen (Cheap Tier), Gemini 2.5 Flash (Model), NotebookLM (Knowledge Engine), OpenRouter (Fallback Router), AI Orchestration Layer, AI Routing Logic (Decision Order), Workflow: Internet Search -> Gemini, Workflow: Upload -> Flashcards (+8 more)

### Community 9 - "API Reference"
Cohesion: 0.14
Nodes (15): API Contract Reference, Analytics API, Auth API, Export API, Image API, Notebook Search API, Notes API, Pagination Convention (+7 more)

### Community 10 - "RAG & Glossary"
Cohesion: 0.19
Nodes (14): RAG Design, Task Type Enum, ADR 0007: Why RAG, Notebook Knowledge Base (Feature), Glossary, Chunk (Term), Document (Term), Generated Material (Term) (+6 more)

### Community 11 - "Auth Tests"
Cohesion: 0.36
Nodes (12): AsyncClient, _register(), test_get_me_requires_valid_token(), test_get_me_returns_profile(), test_google_login_creates_user(), test_google_login_invalid_token_rejected(), test_login_unknown_email_rejected(), test_login_wrong_password_rejected() (+4 more)

### Community 12 - "Architecture & ADR Index"
Cohesion: 0.20
Nodes (11): Backend (FastAPI) Component, Background Processing, Celery + Redis, Frontend Component, Decisions Index (ADR), ADR 0001: Why FastAPI, ADR 0002: Why React, ADR 0003: Why PostgreSQL + Supabase (+3 more)

### Community 13 - "Courses Tests"
Cohesion: 0.60
Nodes (9): _auth(), AsyncClient, _register_and_login(), test_cannot_delete_another_users_course(), test_courses_are_isolated_per_user(), test_create_and_list_courses(), test_create_and_list_subjects(), test_pagination_params() (+1 more)

### Community 14 - "Quiz & Memory"
Cohesion: 0.38
Nodes (7): Memory & Personalization, Workflow: Quiz Submission -> Evaluation -> Progress, Quiz API, quiz_attempts table, quizzes/questions tables, weak_topics table, Weak Topic (Term)

### Community 15 - "RAG Chat Workflow"
Cohesion: 0.40
Nodes (5): Workflow: RAG Chat, Chat API, AI Orchestration Layer (Architecture View), Request Lifecycle, ai_chats table

### Community 28 - "test_orchestrator.py"
Cohesion: 0.05
Nodes (87): GeminiClient, GeminiError, RuntimeError, Gemini provider client (ADR 0005).  The only place `google.genai` is imported (., Raised when the Gemini API call fails, is misconfigured, or returns no usable te, Thin wrapper around the `google-genai` SDK for teaching-explanation calls., Ask Gemini to explain `question`, optionally grounded in `context`.          `co, DocumentIndexResult (+79 more)

### Community 29 - "LocalFileStorage"
Cohesion: 0.08
Nodes (26): AsyncBucketProxy, FileStorage, get_file_storage(), _is_not_found(), LocalFileStorage, Path, File storage abstraction for `Document.storage_path`.  `FileStorage` is the swap, Best-effort translation of a Supabase Storage "object not found" error.      NOT (+18 more)

### Community 30 - "Tech Stack"
Cohesion: 0.06
Nodes (31): ADR 0002: Why React, Alternatives Considered, Consequences, Context, Decision, Status, Tradeoffs, ADR 0003: Why PostgreSQL + Supabase (+23 more)

### Community 31 - "conftest.py"
Cohesion: 0.13
Nodes (18): _parse_document(), parse_document_task(), UUID, Celery tasks for the document parsing pipeline.  Celery workers run sync, but th, Parse an uploaded Document's file and persist the extracted text.      `document, client(), db_session(), _ensure_test_database_exists() (+10 more)

### Community 32 - "ParsedDocument"
Cohesion: 0.11
Nodes (17): ParsedDocument, ParsedSection, Shared result types for document parsers (see app/parsers/registry.py)., Structured result of parsing a document's raw bytes into text.      `text` is th, One natural unit of a parsed document (a PDF page, a PPTX slide, ...).      `ind, parse(), DOCX text extraction (python-docx) — see app/parsers/registry.py for dispatch., Extract paragraph text and metadata from a DOCX's raw bytes.      DOCX has no re (+9 more)

### Community 33 - "NotebookSourceIndexStatus"
Cohesion: 0.24
Nodes (18): attach_source(), create_notebook(), delete_notebook(), detach_source(), get_notebook(), list_notebooks(), CurrentUser, DbSession (+10 more)

### Community 34 - "test_parsers.py"
Cohesion: 0.15
Nodes (18): get_parser(), Dispatch a Document to the parser for its file type.  Looked up by mime_type fir, Raised when no parser is registered for a document's mime_type/file_type., Return the parser function for a document, or raise if none matches., UnsupportedFileTypeError, _docx_bytes(), _pdf_bytes(), _png_bytes() (+10 more)

### Community 35 - "upload_document"
Cohesion: 0.19
Nodes (17): delete_document(), get_document(), _infer_file_type(), list_documents(), CurrentUser, DbSession, UUID, Extension-style fallback signal for `app/parsers/registry.py:get_parser`.      ` (+9 more)

### Community 36 - "CLAUDE.md"
Cohesion: 0.21
Nodes (15): Frontend Rules, Performance Rules, UI Rules, Build API Skill, Celery, FastAPI, Framer Motion, React Hook Form (+7 more)

### Community 37 - "test_notebooks.py"
Cohesion: 0.51
Nodes (14): _auth(), _create_document(), AsyncClient, AsyncSession, _register_and_login(), test_attach_source_creates_source_and_dispatches_indexing(), test_attach_source_rejects_another_users_document(), test_attach_source_requires_parsed_document() (+6 more)

### Community 38 - "test_documents.py"
Cohesion: 0.47
Nodes (13): _auth(), _fake_storage(), AsyncClient, `app.services.document_service.get_file_storage` seam.      Upload tests only ne, _register_and_login(), test_cannot_delete_another_users_document(), test_cannot_get_another_users_document(), test_delete_document_removes_row() (+5 more)

### Community 39 - "Deployment"
Cohesion: 0.18
Nodes (14): Migration Conventions, Deployment, CI/CD (GitHub Actions), Environments (Local/Production), Release Process, Rollback, Security, AI-Specific Risks (+6 more)

### Community 40 - "Architecture Overview"
Cohesion: 0.26
Nodes (12): Architecture Overview, Project Plan, Module Overview, Non-Goals (for now), Target User, Product Vision, Roadmap, Phase 1: Foundation (+4 more)

### Community 41 - "update_me"
Cohesion: 0.33
Nodes (7): get_me(), CurrentUser, DbSession, update_me(), BaseModel, UserRead, UserUpdate

### Community 42 - "_create_document"
Cohesion: 0.62
Nodes (6): _create_document(), AsyncSession, test_get_document_raises_404_when_missing(), test_mark_parse_failed_sets_failed_status(), test_mark_parsed_sets_text_and_done_status(), test_mark_processing_updates_status()

### Community 43 - "ADR 0001: Why FastAPI"
Cohesion: 0.29
Nodes (7): ADR 0001: Why FastAPI, Alternatives Considered, Consequences, Context, Decision, Status, Tradeoffs

### Community 44 - "ADR 0004: Why NotebookLM"
Cohesion: 0.29
Nodes (7): ADR 0004: Why NotebookLM, Alternatives Considered, Consequences, Context, Decision, Status, Tradeoffs

### Community 45 - "ADR 0005: Why Gemini"
Cohesion: 0.29
Nodes (7): ADR 0005: Why Gemini, Alternatives Considered, Consequences, Context, Decision, Status, Tradeoffs

### Community 46 - "ADR 0007: Why RAG"
Cohesion: 0.29
Nodes (7): ADR 0007: Why RAG, Alternatives Considered, Consequences, Context, Decision, Status, Tradeoffs

### Community 47 - "Template Index"
Cohesion: 0.29
Nodes (7): chat_response Template, flashcard_generation Template, formatting_pass Template, note_generation Template, quiz_generation Template, quiz_grading Template, Template Index

## Knowledge Gaps
- **97 isolated node(s):** `lumora-ai`, `ai-tutor-backend`, `Status`, `Context`, `Decision` (+92 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_file_storage()` connect `LocalFileStorage` to `Auth Backend`, `test_orchestrator.py`, `Backend Config & Migrations Setup`, `conftest.py`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `Document` connect `Backend Config & Migrations Setup` to `NotebookSourceIndexStatus`, `test_notebooks.py`, `_create_document`, `test_orchestrator.py`, `conftest.py`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `_index_notebook_source()` connect `test_orchestrator.py` to `LocalFileStorage`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `NotebookLMClient` (e.g. with `test_document_index_rejects_mismatched_request_type()` and `test_document_index_routes_to_notebooklm()`) actually correct?**
  _`NotebookLMClient` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `OrchestrationError` (e.g. with `GeminiClient` and `GeminiError`) actually correct?**
  _`OrchestrationError` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `lumora-ai`, `ai-tutor-backend`, `Status` to the rest of the system?**
  _97 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Auth Backend` be split into smaller, more focused modules?**
  _Cohesion score 0.06829573934837092 - nodes in this community are weakly interconnected._