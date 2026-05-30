# RegFlow AI Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a production-style AI workflow automation platform for regulated operations that demonstrates RAG, approval workflows, and auditability.

**Architecture:** A React frontend talks to a FastAPI control-plane API and a separate AI orchestration service. PostgreSQL + pgvector will back persistent state and retrieval. The first milestone focuses on a strong scaffold, health endpoints, UI shell, and local infra.

**Tech Stack:** React, Vite, TypeScript, FastAPI, pytest, Docker Compose, PostgreSQL, pgvector

---

## Milestone 1 — Foundation
- [x] Monorepo scaffold
- [x] Web app bootstrap
- [x] API service health + metadata endpoints
- [x] AI orchestrator health + recommendation contract
- [x] Docker Compose infra
- [x] Landing dashboard UI

## Milestone 2 — Core domain
- [x] Cases, workflows, audit event schemas
- [ ] Postgres integration
  - [x] SQLite-backed repository abstraction matching planned relational tables
  - [x] Config-driven `DATABASE_URL` detection for sqlite/postgres modes
  - [x] PostgreSQL + pgvector bootstrap SQL artifact at `infra/docker/init/001-regflow-schema.sql`
  - [x] Compose wiring for `DATABASE_URL` and bootstrap volume mounts
  - [ ] Live PostgreSQL runtime verification blocked by Docker socket access in this Hermes session
- [ ] RBAC and auth

## Milestone 3 — AI workflow
- [ ] Document ingestion
- [ ] Retrieval + citations
- [ ] Recommendation generation
- [ ] Approval queue

## Milestone 4 — Portfolio polish
- [ ] Architecture diagram
- [ ] Seed demo data
- [ ] HTTPS deployment
- [ ] Demo video
