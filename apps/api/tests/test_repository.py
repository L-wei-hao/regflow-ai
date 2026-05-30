import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.domain import (
    ActorType,
    AuditEvent,
    CaseRecord,
    CaseStatus,
    RecommendationOutcome,
    WorkflowStep,
    WorkflowStepType,
    WorkflowTemplate,
)
from app.repository import Database, DatabaseConfig, RegFlowRepository


class RepositoryPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "regflow.db"
        self.database = Database(self.db_path)
        self.repository = RegFlowRepository(self.database)
        self.database.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initialize_creates_expected_tables(self) -> None:
        table_names = self.database.list_tables()

        self.assertEqual(
            table_names,
            ["audit_events", "case_records", "workflow_steps", "workflow_templates"],
        )

    def test_workflow_round_trip_persists_steps_and_blocking_sequence(self) -> None:
        workflow = WorkflowTemplate(
            workflow_id="workflow-kyc-v1",
            name="Standard KYC",
            version="1.0.0",
            steps=[
                WorkflowStep("collect-docs", "Collect documents", WorkflowStepType.DOCUMENT_COLLECTION),
                WorkflowStep("retrieve", "Retrieve policy", WorkflowStepType.POLICY_RETRIEVAL),
                WorkflowStep("recommend", "Generate recommendation", WorkflowStepType.AI_RECOMMENDATION),
                WorkflowStep("approve", "Human approval", WorkflowStepType.HUMAN_APPROVAL),
                WorkflowStep("decision", "Final decision", WorkflowStepType.FINAL_DECISION),
            ],
        )

        self.repository.save_workflow(workflow)
        loaded = self.repository.get_workflow("workflow-kyc-v1")

        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.name, "Standard KYC")
        self.assertEqual(loaded.blocking_step_ids(), ["approve", "decision"])
        self.assertEqual(len(loaded.steps), 5)

    def test_case_round_trip_persists_lists_and_reviewer_decision(self) -> None:
        case = CaseRecord.from_intake(
            case_id="case-100",
            workflow_id="workflow-kyc-v1",
            applicant_name="Loh Wei Hao",
            submitted_documents=["passport.pdf", "utility_bill.pdf"],
            policy_tags=["kyc", "proof-of-address"],
        )
        case.start_ai_review()
        case.attach_ai_recommendation(
            outcome=RecommendationOutcome.NEEDS_HUMAN_REVIEW,
            summary="Address proof is outdated.",
            citations=[{"source": "policy.md", "excerpt": "Proof of address must be recent."}],
        )
        case.resolve(
            final_status=CaseStatus.ESCALATED,
            reviewer_id="reviewer-99",
            reviewer_comment="Requested refreshed utility bill.",
        )

        self.repository.save_case(case)
        loaded = self.repository.get_case("case-100")

        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.status, CaseStatus.ESCALATED)
        self.assertEqual(loaded.submitted_documents, ["passport.pdf", "utility_bill.pdf"])
        self.assertEqual(loaded.policy_tags, ["kyc", "proof-of-address"])
        self.assertEqual(loaded.citations[0]["source"], "policy.md")
        self.assertEqual(loaded.assigned_reviewer, "reviewer-99")

    def test_audit_event_round_trip_preserves_actor_and_details(self) -> None:
        event = AuditEvent.for_case_status_change(
            event_id="evt-900",
            case_id="case-100",
            actor_id="reviewer-99",
            actor_type=ActorType.HUMAN_REVIEWER,
            from_status=CaseStatus.AWAITING_HUMAN_APPROVAL,
            to_status=CaseStatus.ESCALATED,
            comment="Missing updated utility bill.",
        )

        self.repository.save_audit_event(event)
        loaded = self.repository.list_audit_events_for_case("case-100")

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].actor_type, ActorType.HUMAN_REVIEWER)
        self.assertEqual(loaded[0].details["to_status"], CaseStatus.ESCALATED.value)


class DatabaseConfigTests(unittest.TestCase):
    def test_from_env_defaults_to_local_sqlite_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {}, clear=True):
                config = DatabaseConfig.from_env(Path(temp_dir))

        self.assertEqual(config.engine, "sqlite")
        self.assertEqual(config.sqlite_path, Path(temp_dir) / "data" / "regflow.db")
        self.assertEqual(config.connection_url, f"sqlite:///{Path(temp_dir) / 'data' / 'regflow.db'}")

    def test_from_env_prefers_database_url_for_postgres(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://regflow:[REDACTED]@postgres:5432/regflow"},
            clear=True,
        ):
            config = DatabaseConfig.from_env(Path("/workspace/regflow-ai"))

        self.assertEqual(config.engine, "postgres")
        self.assertIsNone(config.sqlite_path)
        self.assertEqual(
            config.connection_url,
            "postgresql://regflow:[REDACTED]@postgres:5432/regflow",
        )

    def test_postgres_schema_script_includes_pgvector_extension_and_jsonb_fields(self) -> None:
        config = DatabaseConfig(
            engine="postgres",
            connection_url="postgresql://regflow:[REDACTED]@postgres:5432/regflow",
        )
        database = Database.from_config(config)

        script = database.schema_script()

        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector;", script)
        self.assertIn("submitted_documents_json JSONB NOT NULL", script)
        self.assertIn("policy_tags_json JSONB NOT NULL", script)
        self.assertIn("citations_json JSONB NOT NULL", script)

    def test_write_bootstrap_sql_persists_postgres_schema_artifact(self) -> None:
        config = DatabaseConfig(
            engine="postgres",
            connection_url="postgresql://regflow:[REDACTED]@postgres:5432/regflow",
        )
        database = Database.from_config(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            bootstrap_path = database.write_bootstrap_sql(Path(temp_dir) / "init" / "001-regflow.sql")
            script = bootstrap_path.read_text(encoding="utf-8")

        self.assertTrue(bootstrap_path.name.endswith(".sql"))
        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector;", script)
        self.assertIn("recommendation_embedding VECTOR(1536)", script)


if __name__ == "__main__":
    unittest.main()
