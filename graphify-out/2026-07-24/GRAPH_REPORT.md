# Graph Report - .  (2026-07-24)

## Corpus Check
- Corpus is ~20,055 words - fits in a single context window. You may not need a graph.

## Summary
- 440 nodes · 931 edges · 28 communities (26 shown, 2 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 78 edges (avg confidence: 0.81)
- Token cost: 428,406 input · 0 output

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

## God Nodes (most connected - your core abstractions)
1. `Database Schema Reference` - 32 edges
2. `API Contract Reference` - 26 edges
3. `Features Catalogue` - 24 edges
4. `AI Tutor Project README` - 23 edges
5. `Token & Cost Optimization` - 19 edges
6. `Deployment` - 16 edges
7. `Architect Agent` - 15 edges
8. `get_settings()` - 14 edges
9. `Prompts` - 14 edges
10. `Tech Stack` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Frontend Component` --conceptually_related_to--> `frontend/ Module README`  [INFERRED]
  docs/ARCHITECTURE.md → frontend/README.md
- `Product Roadmap (Phases 1-5)` --conceptually_related_to--> `Features Catalogue`  [INFERRED]
  README.md → docs/FEATURES.md
- `Backend (FastAPI) Component` --conceptually_related_to--> `backend/ Module README`  [INFERRED]
  docs/ARCHITECTURE.md → backend/README.md
- `Background Processing` --semantically_similar_to--> `AI Workflows`  [INFERRED] [semantically similar]
  docs/ARCHITECTURE.md → docs/AI_WORKFLOWS.md
- `Frontend Rules` --references--> `Framer Motion`  [EXTRACTED]
  .claude/rules/frontend.md → CLAUDE.md

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

## Communities (28 total, 2 thin omitted)

### Community 0 - "Auth Backend"
Cohesion: 0.09
Nodes (46): login(), login_google(), DbSession, refresh(), register(), get_me(), CurrentUser, DbSession (+38 more)

### Community 1 - "Claude Agents"
Cohesion: 0.07
Nodes (53): AI Agent, Architect Agent, Backend Agent, Database Agent, DevOps Agent, Documentation Agent, Frontend Agent, Planner Agent (+45 more)

### Community 2 - "Content-Gen Skills & ADRs"
Cohesion: 0.06
Nodes (52): Generate Flashcards Skill, Generate Notes Skill, Generate Quiz Skill, Optimize Prompt Skill, Gemini 2.5 Flash, NotebookLM, ADR Template, ADR 0001: Why FastAPI (+44 more)

### Community 3 - "Repo Rules & Skills"
Cohesion: 0.08
Nodes (44): Frontend Rules, Git Rules, Performance Rules, Security Rules, Testing Rules, UI Rules, Build API Skill, Refactor Module Skill (+36 more)

### Community 4 - "Module READMEs & Features"
Cohesion: 0.07
Nodes (47): ai/ Module README, backend/ Module README, database/ Module README, docker/ Module README, Architecture Overview, Features Catalogue, AI Chat (Feature), AI Evaluation (Feature) (+39 more)

### Community 5 - "Backend Config & Migrations Setup"
Cohesion: 0.10
Nodes (33): do_run_migrations(), get_url(), run_migrations_offline(), run_migrations_online(), get_settings(), Settings, Base, get_db() (+25 more)

### Community 6 - "DB Migration & Core API"
Cohesion: 0.17
Nodes (17): Generate Database Migration Skill, Alembic, Postgres Service (docker-compose.yml), Document API, Notebook API, Auth Flow, PostgreSQL + pgvector, Database Schema Reference (+9 more)

### Community 7 - "Courses Backend"
Cohesion: 0.36
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
Cohesion: 0.18
Nodes (12): Backend (FastAPI) Component, Background Processing, Celery + Redis, Frontend Component, Decisions Index (ADR), ADR 0001: Why FastAPI, ADR 0002: Why React, ADR 0003: Why PostgreSQL + Supabase (+4 more)

### Community 13 - "Courses Tests"
Cohesion: 0.60
Nodes (9): _auth(), AsyncClient, _register_and_login(), test_cannot_delete_another_users_course(), test_courses_are_isolated_per_user(), test_create_and_list_courses(), test_create_and_list_subjects(), test_pagination_params() (+1 more)

### Community 14 - "Quiz & Memory"
Cohesion: 0.38
Nodes (7): Memory & Personalization, Workflow: Quiz Submission -> Evaluation -> Progress, Quiz API, quiz_attempts table, quizzes/questions tables, weak_topics table, Weak Topic (Term)

### Community 15 - "RAG Chat Workflow"
Cohesion: 0.40
Nodes (5): Workflow: RAG Chat, Chat API, AI Orchestration Layer (Architecture View), Request Lifecycle, ai_chats table

## Knowledge Gaps
- **54 isolated node(s):** `ai-tutor-backend`, `/changelog-entry Command`, `Architecture Decision Record (ADR)`, `docs/AI_WORKFLOWS.md`, `docs/FOLDER_STRUCTURE.md` (+49 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database Schema Reference` connect `DB Migration & Core API` to `Content-Gen Skills & ADRs`, `Repo Rules & Skills`, `Module READMEs & Features`, `AI Model Routing`, `API Reference`, `Architecture & ADR Index`, `Quiz & Memory`, `RAG Chat Workflow`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `API Contract Reference` connect `API Reference` to `Content-Gen Skills & ADRs`, `Repo Rules & Skills`, `Module READMEs & Features`, `DB Migration & Core API`, `AI Model Routing`, `Quiz & Memory`, `RAG Chat Workflow`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `Features Catalogue` connect `Module READMEs & Features` to `RAG & Glossary`, `Content-Gen Skills & ADRs`, `Repo Rules & Skills`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **What connects `ai-tutor-backend`, `/changelog-entry Command`, `Architecture Decision Record (ADR)` to the rest of the system?**
  _54 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Auth Backend` be split into smaller, more focused modules?**
  _Cohesion score 0.09220779220779221 - nodes in this community are weakly interconnected._
- **Should `Claude Agents` be split into smaller, more focused modules?**
  _Cohesion score 0.07039187227866474 - nodes in this community are weakly interconnected._
- **Should `Content-Gen Skills & ADRs` be split into smaller, more focused modules?**
  _Cohesion score 0.06108597285067873 - nodes in this community are weakly interconnected._