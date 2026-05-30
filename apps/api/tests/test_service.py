import tempfile
import unittest
from pathlib import Path

from app.access import AccessControl, UserPrincipal, UserRole
from app.domain import CaseStatus, RecommendationOutcome, WorkflowStep, WorkflowStepType, WorkflowTemplate
from app.repository import Database, DatabaseConfig, RegFlowRepository
from app.service import RegFlowService


class RegFlowServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        project_root = Path(self.tempdir.name)
        config = DatabaseConfig(engine="sqlite", connection_url="sqlite:///:memory:", sqlite_path=project_root / "regflow.sqlite3")
        self.database = Database.from_config(config)
        self.database.initialize()
        self.repository = RegFlowRepository(self.database)
        self.service = RegFlowService(self.repository, AccessControl())
        self.admin = UserPrincipal(user_id="admin-1", display_name="Admin", role=UserRole.ADMIN)
        self.reviewer = UserPrincipal(user_id="reviewer-1", display_name="Reviewer", role=UserRole.REVIEWER)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_register_workflow_create_case_and_resolve_with_audit_trail(self) -> None:
        workflow = WorkflowTemplate(
            workflow_id="kyc-standard",
            name="Standard KYC",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="collect-docs",
                    name="Collect documents",
                    step_type=WorkflowStepType.DOCUMENT_COLLECTION,
                ),
                WorkflowStep(
                    step_id="review",
                    name="Human approval",
                    step_type=WorkflowStepType.HUMAN_APPROVAL,
                ),
                WorkflowStep(
                    step_id="decision",
                    name="Final decision",
                    step_type=WorkflowStepType.FINAL_DECISION,
                ),
            ],
        )

        self.service.register_workflow(self.admin, workflow)
        case = self.service.create_case(
            self.admin,
            case_id="case-100",
            workflow_id="kyc-standard",
            applicant_name="Jane Tan",
            submitted_documents=["passport.pdf"],
            policy_tags=["kyc"],
        )

        self.assertEqual(case.status, CaseStatus.INTAKE_SUBMITTED)

        case = self.service.start_ai_review(self.admin, "case-100")
        case = self.service.record_ai_recommendation(
            self.admin,
            case_id="case-100",
            outcome=RecommendationOutcome.NEEDS_HUMAN_REVIEW,
            summary="Proof of address is missing.",
            citations=[{"source": "policy.md", "excerpt": "Proof of address is required."}],
        )

        pending = self.service.list_pending_approvals(self.reviewer)
        self.assertEqual([item.case_id for item in pending], ["case-100"])

        resolved = self.service.resolve_case(
            self.reviewer,
            case_id="case-100",
            final_status=CaseStatus.ESCALATED,
            reviewer_comment="Escalated until proof of address is supplied.",
        )

        self.assertEqual(resolved.status, CaseStatus.ESCALATED)
        self.assertEqual(resolved.assigned_reviewer, "reviewer-1")
        audit_events = self.service.get_case_audit_trail(self.admin, "case-100")
        self.assertGreaterEqual(len(audit_events), 1)
        self.assertEqual(audit_events[-1].details["to_status"], CaseStatus.ESCALATED.value)

    def test_reviewer_cannot_register_workflows(self) -> None:
        workflow = WorkflowTemplate(
            workflow_id="kyc-standard",
            name="Standard KYC",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="collect-docs",
                    name="Collect documents",
                    step_type=WorkflowStepType.DOCUMENT_COLLECTION,
                ),
                WorkflowStep(
                    step_id="review",
                    name="Human approval",
                    step_type=WorkflowStepType.HUMAN_APPROVAL,
                ),
            ],
        )

        with self.assertRaises(PermissionError):
            self.service.register_workflow(self.reviewer, workflow)


if __name__ == "__main__":
    unittest.main()
