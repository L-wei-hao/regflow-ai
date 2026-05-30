# RegFlow AI

> **AI workflow automation platform for regulated operations.**

[![CI](https://github.com/L-wei-hao/regflow-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/L-wei-hao/regflow-ai/actions/workflows/ci.yml)

RegFlow AI is a recruiter-friendly flagship project that demonstrates how to design and ship AI systems for compliance-heavy environments: case management, workflow automation, retrieval with citations, approval gates, and auditability.

## Why this project stands out

Most portfolio projects are either:
- a generic CRUD app, or
- a chatbot wrapped around an API.

RegFlow AI is different. It shows:
- **AI + enterprise workflow design**
- **regulated-domain thinking**
- **human-in-the-loop controls**
- **auditability and traceability**
- **backend + frontend + infra in one coherent product**

That combination makes it much easier to discuss in interviews for AI integration, solutions engineering, and automation roles.

## What it does

RegFlow AI helps teams safely apply AI to workflows where decisions matter, such as:
- KYC / onboarding review
- policy-guided case handling
- internal approvals
- evidence-based operational decisions

## Core product capabilities

- Markdown policy ingestion pipeline that chunks documents for retrieval
- Case creation and review workflow
- AI recommendation endpoint with grounded citations
- Human approval gate for sensitive decisions
- End-to-end audit trail
- PostgreSQL-ready persistence with local SQLite fallback for development

## Tech stack

- **Frontend:** React + Vite
- **API:** Python service layer with FastAPI-style structure
- **AI service:** lightweight orchestrator service for retrieval/recommendations
- **Persistence:** SQLite locally, PostgreSQL bootstrap SQL for Compose deployment
- **Infra:** Docker Compose, GitHub Actions

## Architecture

```text
[React Web App]
        |
        v
[Control Plane API] <-----> [PostgreSQL + pgvector]
        |
        v
[AI Orchestrator] -----> [LLM / embedding provider]
```

## Repository layout

- `apps/web` — dashboard UI and review experience
- `apps/api` — control plane for cases, workflows, approvals, and audit events
- `apps/ai-orchestrator` — recommendation and retrieval scaffolding
- `infra/docker` — local deployment assets and database bootstrap SQL
- `docs/` — plans, architecture notes, and roadmap docs

## Local development

### 1) Run the web app

```bash
cd apps/web
npm install
npm run dev
```

### 2) Run the API tests

```bash
cd apps/api
PYTHONPATH=. python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### 3) Run the Python services in a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt -r apps/ai-orchestrator/requirements.txt
pytest apps/api/tests apps/ai-orchestrator/tests -q
```

### 4) Run the full stack with Docker Compose

```bash
docker compose up --build
```

## Production-style HTTPS deployment with Caddy

For a recruiter-facing live demo, serve the built frontend with Caddy and proxy API requests to the FastAPI service.

```bash
# Build the frontend
cd apps/web
npm run build

# Start the API on localhost:8000
cd ../api
PYTHONPATH=. python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# In another terminal, start Caddy from the repo root
cd ../../
export PUBLIC_HOST=YOUR_PUBLIC_IP.nip.io
export API_UPSTREAM=127.0.0.1:8000
export WEB_ROOT=/home/weihao95/workspace/regflow-ai/apps/web/dist
export LOG_FILE=/home/weihao95/workspace/regflow-ai/logs/caddy.log
sudo caddy run --config infra/caddy/Caddyfile --adapter caddyfile
```

The Caddy config:
- serves the React build from `apps/web/dist`
- proxies `/api/*` and `/health` to the backend
- enables HTTPS, compression, and security headers

## Verification

The repository currently includes automated checks for:
- API domain logic
- repository configuration and schema generation
- orchestrator response shaping
- frontend build/lint in CI

## CI

GitHub Actions runs on every push and pull request:
- backend test suite
- frontend install, lint, and build

## Roadmap

### Done
- [x] Authentication and RBAC
- [x] Case and workflow CRUD services
- [x] Human approval queue
- [x] Audit trail backend
- [x] Live dashboard wired to the API
- [x] Case detail and audit timeline UI
- [x] Retrieval pipeline and citations
- [x] Policy/document ingestion pipelines

### Next
- [ ] Live PostgreSQL + pgvector runtime verification
- [ ] Production deployment over HTTPS

## Resume angle

This repository is designed to help me explain:
- how I design systems for regulated environments
- how I combine AI with workflow automation responsibly
- how I think about auditability, approval controls, and deployment
- how I move from prototype to production-style architecture

## Next improvements

If you want to make this even stronger, the highest-value additions are:
1. a short demo video or GIF
2. a polished architecture diagram
3. authenticated user flows and RBAC
4. a real end-to-end approval workflow
5. live deployed environment over HTTPS
