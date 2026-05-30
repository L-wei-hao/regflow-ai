from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.domain import AuditEvent, CaseRecord, WorkflowStep, WorkflowTemplate

DatabaseEngine = Literal["sqlite", "postgres"]


@dataclass(frozen=True)
class DatabaseConfig:
    engine: DatabaseEngine
    connection_url: str
    sqlite_path: Path | None = None

    @classmethod
    def from_env(cls, project_root: Path) -> "DatabaseConfig":
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            normalized = database_url.strip()
            if normalized.startswith(("postgres://", "postgresql://")):
                return cls(engine="postgres", connection_url=normalized)
            if normalized.startswith("sqlite:///"):
                sqlite_path = Path(normalized.removeprefix("sqlite:///"))
                return cls(engine="sqlite", connection_url=normalized, sqlite_path=sqlite_path)
            raise ValueError(
                "Unsupported DATABASE_URL scheme. Expected postgres://, postgresql://, or sqlite:///"
            )

        sqlite_path = Path(project_root) / "data" / "regflow.db"
        return cls(
            engine="sqlite",
            connection_url=f"sqlite:///{sqlite_path}",
            sqlite_path=sqlite_path,
        )


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config = DatabaseConfig(
            engine="sqlite",
            connection_url=f"sqlite:///{self.path}",
            sqlite_path=self.path,
        )

    @classmethod
    def from_config(cls, config: DatabaseConfig) -> "Database":
        if config.engine == "sqlite":
            if config.sqlite_path is None:
                raise ValueError("sqlite_path is required for sqlite configuration")
            return cls(config.sqlite_path)

        database = cls.__new__(cls)
        database.config = config
        database.path = None
        return database

    def connect(self) -> sqlite3.Connection:
        if self.config.engine != "sqlite":
            raise NotImplementedError(
                "Direct PostgreSQL connections are not available in this dependency-light scaffold yet. "
                "Use schema_script() / write_bootstrap_sql() artifacts or run through Docker Compose."
            )

        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        if self.config.engine != "sqlite":
            raise NotImplementedError(
                "Use write_bootstrap_sql() to prepare PostgreSQL initialization artifacts."
            )

        with self.connect() as connection:
            connection.executescript(self.schema_script())

    def schema_script(self) -> str:
        if self.config.engine == "postgres":
            return """
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
""".strip()

        return """
CREATE TABLE IF NOT EXISTS workflow_templates (
    workflow_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    regulated INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    workflow_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    step_id TEXT NOT NULL,
    name TEXT NOT NULL,
    step_type TEXT NOT NULL,
    PRIMARY KEY (workflow_id, step_id),
    FOREIGN KEY (workflow_id) REFERENCES workflow_templates(workflow_id)
);

CREATE TABLE IF NOT EXISTS case_records (
    case_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    applicant_name TEXT NOT NULL,
    submitted_documents_json TEXT NOT NULL,
    policy_tags_json TEXT NOT NULL,
    status TEXT NOT NULL,
    ai_outcome TEXT,
    ai_summary TEXT,
    citations_json TEXT NOT NULL,
    assigned_reviewer TEXT,
    reviewer_comment TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflow_templates(workflow_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    details_json TEXT NOT NULL
);
""".strip()

    def write_bootstrap_sql(self, destination: Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(f"{self.schema_script()}\n", encoding="utf-8")
        return destination

    def list_tables(self) -> list[str]:
        if self.config.engine != "sqlite":
            raise NotImplementedError(
                "Table listing is only available for live SQLite verification in this scaffold."
            )

        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row[0] for row in rows]


class RegFlowRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save_workflow(self, workflow: WorkflowTemplate) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_templates (workflow_id, name, version, regulated)
                VALUES (:workflow_id, :name, :version, :regulated)
                ON CONFLICT(workflow_id) DO UPDATE SET
                    name = excluded.name,
                    version = excluded.version,
                    regulated = excluded.regulated
                """,
                {
                    **workflow.to_record(),
                    "regulated": int(workflow.regulated),
                },
            )
            connection.execute(
                "DELETE FROM workflow_steps WHERE workflow_id = ?",
                (workflow.workflow_id,),
            )
            connection.executemany(
                """
                INSERT INTO workflow_steps (workflow_id, step_order, step_id, name, step_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        workflow.workflow_id,
                        index,
                        step.step_id,
                        step.name,
                        step.step_type.value,
                    )
                    for index, step in enumerate(workflow.steps)
                ],
            )

    def get_workflow(self, workflow_id: str) -> WorkflowTemplate | None:
        with self.database.connect() as connection:
            workflow_row = connection.execute(
                "SELECT workflow_id, name, version, regulated FROM workflow_templates WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
            if workflow_row is None:
                return None
            step_rows = connection.execute(
                """
                SELECT step_id, name, step_type
                FROM workflow_steps
                WHERE workflow_id = ?
                ORDER BY step_order ASC
                """,
                (workflow_id,),
            ).fetchall()

        return WorkflowTemplate(
            workflow_id=workflow_row["workflow_id"],
            name=workflow_row["name"],
            version=workflow_row["version"],
            regulated=bool(workflow_row["regulated"]),
            steps=[
                WorkflowStep.from_dict(
                    {
                        "step_id": row["step_id"],
                        "name": row["name"],
                        "step_type": row["step_type"],
                    }
                )
                for row in step_rows
            ],
        )

    def save_case(self, case: CaseRecord) -> None:
        payload = case.to_record()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO case_records (
                    case_id,
                    workflow_id,
                    applicant_name,
                    submitted_documents_json,
                    policy_tags_json,
                    status,
                    ai_outcome,
                    ai_summary,
                    citations_json,
                    assigned_reviewer,
                    reviewer_comment
                )
                VALUES (
                    :case_id,
                    :workflow_id,
                    :applicant_name,
                    :submitted_documents_json,
                    :policy_tags_json,
                    :status,
                    :ai_outcome,
                    :ai_summary,
                    :citations_json,
                    :assigned_reviewer,
                    :reviewer_comment
                )
                ON CONFLICT(case_id) DO UPDATE SET
                    workflow_id = excluded.workflow_id,
                    applicant_name = excluded.applicant_name,
                    submitted_documents_json = excluded.submitted_documents_json,
                    policy_tags_json = excluded.policy_tags_json,
                    status = excluded.status,
                    ai_outcome = excluded.ai_outcome,
                    ai_summary = excluded.ai_summary,
                    citations_json = excluded.citations_json,
                    assigned_reviewer = excluded.assigned_reviewer,
                    reviewer_comment = excluded.reviewer_comment
                """,
                {
                    "case_id": payload["case_id"],
                    "workflow_id": payload["workflow_id"],
                    "applicant_name": payload["applicant_name"],
                    "submitted_documents_json": json.dumps(payload["submitted_documents"]),
                    "policy_tags_json": json.dumps(payload["policy_tags"]),
                    "status": payload["status"],
                    "ai_outcome": payload["ai_outcome"],
                    "ai_summary": payload["ai_summary"],
                    "citations_json": json.dumps(payload["citations"]),
                    "assigned_reviewer": payload["assigned_reviewer"],
                    "reviewer_comment": payload["reviewer_comment"],
                },
            )

    def get_case(self, case_id: str) -> CaseRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM case_records WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            return None
        return CaseRecord.from_record(
            {
                "case_id": row["case_id"],
                "workflow_id": row["workflow_id"],
                "applicant_name": row["applicant_name"],
                "submitted_documents": json.loads(row["submitted_documents_json"]),
                "policy_tags": json.loads(row["policy_tags_json"]),
                "status": row["status"],
                "ai_outcome": row["ai_outcome"],
                "ai_summary": row["ai_summary"],
                "citations": json.loads(row["citations_json"]),
                "assigned_reviewer": row["assigned_reviewer"],
                "reviewer_comment": row["reviewer_comment"],
            }
        )

    def save_audit_event(self, event: AuditEvent) -> None:
        payload = event.to_dict()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    event_id,
                    entity_type,
                    entity_id,
                    action,
                    actor_id,
                    actor_type,
                    occurred_at,
                    details_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    entity_type = excluded.entity_type,
                    entity_id = excluded.entity_id,
                    action = excluded.action,
                    actor_id = excluded.actor_id,
                    actor_type = excluded.actor_type,
                    occurred_at = excluded.occurred_at,
                    details_json = excluded.details_json
                """,
                (
                    payload["event_id"],
                    payload["entity_type"],
                    payload["entity_id"],
                    payload["action"],
                    payload["actor"]["id"],
                    payload["actor"]["type"],
                    payload["occurred_at"],
                    json.dumps(payload["details"]),
                ),
            )

    def list_audit_events_for_case(self, case_id: str) -> list[AuditEvent]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM audit_events
                WHERE entity_type = 'case' AND entity_id = ?
                ORDER BY occurred_at ASC
                """,
                (case_id,),
            ).fetchall()
        return [
            AuditEvent.from_record(
                {
                    "event_id": row["event_id"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "action": row["action"],
                    "actor_id": row["actor_id"],
                    "actor_type": row["actor_type"],
                    "occurred_at": row["occurred_at"],
                    "details": json.loads(row["details_json"]),
                }
            )
            for row in rows
        ]
