# RegFlow AI Architecture

## Product intent

RegFlow AI is built to show how AI can be used safely in regulated operations without turning every decision into a black box. The system balances automation with oversight.

## Design principles

1. **Human override first**
   - High-risk recommendations should default to review, not automatic execution.

2. **Traceability over magic**
   - Every action should leave an audit trail.

3. **Grounded AI**
   - Recommendations should cite sources or retrieved policy snippets.

4. **Deployment realism**
   - Local dev should work without special infrastructure.
   - Production should be PostgreSQL-ready and HTTPS-ready.

## Component model

- **Web app**
  - Review dashboard
  - Case detail views
  - Approval queue
  - Audit timeline

- **Control plane API**
  - Case and workflow orchestration
  - Persistence and schema management
  - Audit/event recording
  - Approval state transitions

- **AI orchestrator**
  - Retrieval-driven recommendation generation
  - Citation selection
  - Suggestion shaping for human review

- **Database layer**
  - SQLite for local development and tests
  - PostgreSQL + pgvector bootstrap for real deployments

## Request flow

```text
User action
  -> Web app
  -> Control plane API
  -> Database / audit log
  -> AI orchestrator (if recommendation is needed)
  -> Human review / approval
  -> Final state change recorded
```

## Security posture

- Sensitive actions should be approval-gated.
- Audit logs should record who did what and when.
- Recommendation output should be explainable.
- Production deployment should use HTTPS.

## What makes this portfolio-worthy

This project demonstrates:
- product thinking
- backend architecture
- workflow design
- compliance awareness
- AI system boundaries
- practical deployment concerns
