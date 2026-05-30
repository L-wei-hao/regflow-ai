import unittest

from app.domain import (
    ActorType,
    AuditAction,
    AuditEvent,
    CaseRecord,
    CaseStatus,
    RecommendationOutcome,
    WorkflowStep,
    WorkflowStepType,
    WorkflowTemplate,
)


class CaseRecordTests(unittest.TestCase):
    def test_from_intake_creates_case_ready_for_review(self) -> None:
        case = CaseRecord.from_intake(
            case_id="case-001",
            workflow_id="kyc-standard",
            applicant_name="Jane Tan",
            submitted_documents=["passport.pdf", "utility_bill.pdf"],
            policy_tags=["kyc", "proof-of-address"],
        )

        self.assertEqual(case.status, CaseStatus.INTAKE_SUBMITTED)
        self.assertEqual(case.submitted_documents, ["passport.pdf", "utility_bill.pdf"])
        self.assertEqual(case.policy_tags, ["kyc", "proof-of-address"])
        self.assertIsNone(case.ai_summary)

    def test_case_can_transition_through_review_and_final_resolution(self) -> None:
        case = CaseRecord.from_intake(
            case_id="case-002",
            workflow_id="kyc-standard",
            applicant_name="Wei Hao Loh",
            submitted_documents=["passport.pdf"],
            policy_tags=["kyc"],
        )

        case.start_ai_review()
        case.attach_ai_recommendation(
            outcome=RecommendationOutcome.NEEDS_HUMAN_REVIEW,
            summary="Missing proof of address document.",
            citations=[{"source": "policy.md", "excerpt": "Proof of address is required."}],
        )
        case.resolve(
            final_status=CaseStatus.ESCALATED,
            reviewer_id="reviewer-01",
            reviewer_comment="Escalated pending additional customer documents.",
        )

        self.assertEqual(case.status, CaseStatus.ESCALATED)
        self.assertEqual(case.assigned_reviewer, "reviewer-01")
        self.assertEqual(case.ai_summary, "Missing proof of address document.")
        self.assertEqual(case.citations[0]["source"], "policy.md")

    def test_invalid_resolution_before_ai_recommendation_is_rejected(self) -> None:
        case = CaseRecord.from_intake(
            case_id="case-003",
            workflow_id="kyc-standard",
            applicant_name="John Doe",
            submitted_documents=["passport.pdf"],
            policy_tags=["kyc"],
        )

        case.start_ai_review()

        with self.assertRaises(ValueError):
            case.resolve(
                final_status=CaseStatus.APPROVED,
                reviewer_id="reviewer-02",
                reviewer_comment="Approved too early.",
            )


class WorkflowTemplateTests(unittest.TestCase):
    def test_regulated_workflow_requires_human_approval_step(self) -> None:
        with self.assertRaises(ValueError):
            WorkflowTemplate(
                workflow_id="workflow-001",
                name="Unsafe workflow",
                version="1.0.0",
                steps=[
                    WorkflowStep(
                        step_id="retrieve-policy",
                        name="Retrieve policy",
                        step_type=WorkflowStepType.POLICY_RETRIEVAL,
                    ),
                    WorkflowStep(
                        step_id="recommend",
                        name="Generate recommendation",
                        step_type=WorkflowStepType.AI_RECOMMENDATION,
                    ),
                ],
            )

    def test_duplicate_step_ids_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            WorkflowTemplate(
                workflow_id="workflow-002",
                name="Duplicate steps",
                version="1.0.0",
                steps=[
                    WorkflowStep(
                        step_id="approve",
                        name="Approve",
                        step_type=WorkflowStepType.HUMAN_APPROVAL,
                    ),
                    WorkflowStep(
                        step_id="approve",
                        name="Final approval",
                        step_type=WorkflowStepType.FINAL_DECISION,
                    ),
                ],
            )

    def test_valid_workflow_exposes_blocking_step_sequence(self) -> None:
        workflow = WorkflowTemplate(
            workflow_id="workflow-003",
            name="Standard KYC",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    step_id="collect-docs",
                    name="Collect documents",
                    step_type=WorkflowStepType.DOCUMENT_COLLECTION,
                ),
                WorkflowStep(
                    step_id="recommend",
                    name="Generate recommendation",
                    step_type=WorkflowStepType.AI_RECOMMENDATION,
                ),
                WorkflowStep(
                    step_id="approve",
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

        self.assertEqual(
            workflow.blocking_step_ids(),
            ["approve", "decision"],
        )


class AuditEventTests(unittest.TestCase):
    def test_for_case_status_change_captures_metadata(self) -> None:
        event = AuditEvent.for_case_status_change(
            event_id="evt-001",
            case_id="case-001",
            actor_id="reviewer-01",
            actor_type=ActorType.HUMAN_REVIEWER,
            from_status=CaseStatus.AWAITING_HUMAN_APPROVAL,
            to_status=CaseStatus.APPROVED,
            comment="All required documents verified.",
        )

        payload = event.to_dict()

        self.assertEqual(payload["action"], AuditAction.CASE_STATUS_CHANGED.value)
        self.assertEqual(payload["entity_type"], "case")
        self.assertEqual(payload["details"]["from_status"], CaseStatus.AWAITING_HUMAN_APPROVAL.value)
        self.assertEqual(payload["details"]["to_status"], CaseStatus.APPROVED.value)
        self.assertEqual(payload["actor"]["type"], ActorType.HUMAN_REVIEWER.value)


if __name__ == "__main__":
    unittest.main()
