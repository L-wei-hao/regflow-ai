CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS workflow_templates (
    workflow_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    regulated BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    workflow_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    step_id TEXT NOT NULL,
    name TEXT NOT NULL,
    step_type TEXT NOT NULL,
    PRIMARY KEY (workflow_id, step_id),
    CONSTRAINT fk_workflow_steps_template
        FOREIGN KEY (workflow_id)
        REFERENCES workflow_templates(workflow_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS case_records (
    case_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    applicant_name TEXT NOT NULL,
    submitted_documents_json JSONB NOT NULL,
    policy_tags_json JSONB NOT NULL,
    status TEXT NOT NULL,
    ai_outcome TEXT,
    ai_summary TEXT,
    citations_json JSONB NOT NULL,
    assigned_reviewer TEXT,
    reviewer_comment TEXT,
    recommendation_embedding VECTOR(1536),
    CONSTRAINT fk_case_records_template
        FOREIGN KEY (workflow_id)
        REFERENCES workflow_templates(workflow_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    details_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_case_records_workflow_id
    ON case_records (workflow_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_case_lookup
    ON audit_events (entity_type, entity_id, occurred_at);
