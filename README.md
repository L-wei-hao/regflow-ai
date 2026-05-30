# RegFlow AI

> AI workflow automation platform for regulated operations.

RegFlow AI is a flagship portfolio project designed to demonstrate production-style AI engineering for compliance-heavy operations. The platform combines retrieval-augmented generation (RAG), human approval gates, audit logs, document ingestion, and case management in a single monorepo.

## Current scaffold

- `apps/web` — React + Vite frontend for dashboards, workflows, and case review
- `apps/api` — FastAPI control plane for cases, workflows, audit events, and approvals
- `apps/ai-orchestrator` — FastAPI AI service for retrieval, recommendations, and explainability
- `infra/docker` — local infrastructure assets
- `docs/` — plans, architecture, screenshots, and project documentation

## Product vision

RegFlow AI helps teams safely apply AI to regulated workflows such as KYC review, policy-guided case handling, and internal operations approval flows.

### MVP capabilities

1. Document ingestion into a vector-ready knowledge base
2. Case creation and review workflow
3. AI recommendation endpoint with grounded citations
4. Human approval gate for sensitive decisions
5. End-to-end audit trail

## Architecture

```text
React Web App
   |
   v
FastAPI Control Plane  <----> PostgreSQL + pgvector
   |
   v
AI Orchestrator Service -----> LLM / Embedding providers
```

## Local development

### Web

```bash
cd apps/web
npm install
npm run dev
```

### API tests (current stdlib-compatible path)

```bash
cd apps/api
PYTHONPATH=. /usr/bin/python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### Python services (future FastAPI path)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt -r apps/ai-orchestrator/requirements.txt
pytest apps/api/tests apps/ai-orchestrator/tests -q
```

### Infra

```bash
docker compose up --build
```

PostgreSQL bootstrap SQL is generated at:
- `infra/docker/init/001-regflow-schema.sql`
- `apps/api/sql/001-regflow-schema.sql`

The API and AI orchestrator both read `DATABASE_URL`, defaulting to PostgreSQL in Compose and falling back to local SQLite when `DATABASE_URL` is absent.

## Roadmap

- [ ] Live PostgreSQL + pgvector runtime verification
- [ ] Authentication and RBAC
- [ ] Case and workflow CRUD
- [ ] Retrieval pipeline and citations
- [ ] Human approval queue
- [ ] Audit timeline UI
- [ ] Production deployment over HTTPS
