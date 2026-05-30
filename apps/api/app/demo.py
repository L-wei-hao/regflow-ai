from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Any

from app.access import UserPrincipal, UserRole
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
from app.service import RegFlowService

RUNTIME_ROOT = Path(gettempdir()) / "regflow-ai"
DEMO_DATABASE_PATH = RUNTIME_ROOT / "demo.sqlite3"


def _demo_principals() -> tuple[UserPrincipal, UserPrincipal]:
    return (
        UserPrincipal(user_id="admin-001", display_name="Aisha Rahman", role=UserRole.ADMIN),
        UserPrincipal(user_id="reviewer-001", display_name="Marcus Lee", role=UserRole.REVIEWER),
    )


def _seed_demo_data(service: RegFlowService) -> None:
    admin, reviewer = _demo_principals()

    kyc_workflow = WorkflowTemplate(
        workflow_id="kyc-standard",
        name="Standard KYC Review",
        version="1.3.0",
        steps=[
            WorkflowStep(
                step_id="collect-docs",
                name="Collect supporting documents",
                step_type=WorkflowStepType.DOCUMENT_COLLECTION,
            ),
            WorkflowStep(
                step_id="policy-check",
                name="Retrieve policy guidance",
                step_type=WorkflowStepType.POLICY_RETRIEVAL,
            ),
            WorkflowStep(
                step_id="ai-review",
                name="Generate AI recommendation",
                step_type=WorkflowStepType.AI_RECOMMENDATION,
            ),
            WorkflowStep(
                step_id="human-approval",
                name="Human approval",
                step_type=WorkflowStepType.HUMAN_APPROVAL,
            ),
            WorkflowStep(
                step_id="final-decision",
                name="Final decision",
                step_type=WorkflowStepType.FINAL_DECISION,
            ),
        ],
    )

    sanctions_workflow = WorkflowTemplate(
        workflow_id="sanctions-escalation",
        name="Sanctions Escalation Workflow",
        version="1.0.0",
        steps=[
            WorkflowStep(
                step_id="collect-evidence",
                name="Collect evidence package",
                step_type=WorkflowStepType.DOCUMENT_COLLECTION,
            ),
            WorkflowStep(
                step_id="policy-retrieval",
                name="Surface policy excerpts",
                step_type=WorkflowStepType.POLICY_RETRIEVAL,
            ),
            WorkflowStep(
                step_id="review-board",
                name="Escalation board approval",
                step_type=WorkflowStepType.HUMAN_APPROVAL,
            ),
            WorkflowStep(
                step_id="decision",
                name="Disposition decision",
                step_type=WorkflowStepType.FINAL_DECISION,
            ),
        ],
    )

    service.register_workflow(admin, kyc_workflow)
    service.register_workflow(admin, sanctions_workflow)

    service.create_case(
        admin,
        case_id="case-001",
        workflow_id="kyc-standard",
        applicant_name="Jane Tan",
        submitted_documents=["passport.pdf", "proof-of-address.pdf"],
        policy_tags=["kyc", "residential-verification"],
    )
    service.start_ai_review(admin, "case-001")
    service.record_ai_recommendation(
        admin,
        case_id="case-001",
        outcome=RecommendationOutcome.NEEDS_HUMAN_REVIEW,
        summary="The address document is valid, but the proof-of-income file requires manual confirmation.",
        citations=[
            {
                "source": "policy/kyc-standard.md",
                "excerpt": "Incomplete income evidence should be routed to human approval before onboarding.",
            }
        ],
    )

    service.create_case(
        admin,
        case_id="case-002",
        workflow_id="kyc-standard",
        applicant_name="Suresh Kumar",
        submitted_documents=["passport.pdf", "salary-slip.pdf", "proof-of-address.pdf"],
        policy_tags=["kyc", "low-risk"],
    )
    service.start_ai_review(admin, "case-002")
    service.record_ai_recommendation(
        admin,
        case_id="case-002",
        outcome=RecommendationOutcome.APPROVE,
        summary="All required documents are present and the policy checks are clean.",
        citations=[
            {
                "source": "policy/kyc-standard.md",
                "excerpt": "Approve when identity and address evidence are complete and no escalation flags are present.",
            }
        ],
    )
    service.resolve_case(
        reviewer,
        case_id="case-002",
        final_status=CaseStatus.APPROVED,
        reviewer_comment="Approved after spot-checking the cited policy references.",
    )

    service.create_case(
        admin,
        case_id="case-003",
        workflow_id="sanctions-escalation",
        applicant_name="Acme Trading Pte. Ltd.",
        submitted_documents=["incorporation-cert.pdf", "beneficial-owners.csv"],
        policy_tags=["sanctions", "trade-finance"],
    )
    service.start_ai_review(admin, "case-003")
    service.record_ai_recommendation(
        admin,
        case_id="case-003",
        outcome=RecommendationOutcome.ESCALATE,
        summary="A beneficial owner name loosely matches a sanctions screening result and needs escalation.",
        citations=[
            {
                "source": "policy/sanctions-escalation.md",
                "excerpt": "Potential sanctions matches must be escalated to the review board with supporting context.",
            }
        ],
    )
    service.resolve_case(
        reviewer,
        case_id="case-003",
        final_status=CaseStatus.ESCALATED,
        reviewer_comment="Escalated to the review board with the policy excerpt attached.",
    )


@lru_cache(maxsize=1)
def get_demo_service() -> RegFlowService:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    config = DatabaseConfig(
        engine="sqlite",
        connection_url=f"sqlite:///{DEMO_DATABASE_PATH}",
        sqlite_path=DEMO_DATABASE_PATH,
    )
    database = Database.from_config(config)
    database.initialize()
    repository = RegFlowRepository(database)
    service = RegFlowService(repository)

    if not repository.list_workflows():
        _seed_demo_data(service)

    return service


def humanize(value: str) -> str:
    return value.replace("_", " ").title()


def workflow_to_payload(workflow: WorkflowTemplate) -> dict[str, Any]:
    return {
        **workflow.to_record(),
        "regulated": workflow.regulated,
        "step_count": len(workflow.steps),
        "blocking_steps": workflow.blocking_step_ids(),
        "steps": [step.to_dict() for step in workflow.steps],
    }


def case_to_payload(case: CaseRecord, audit_events: list[AuditEvent] | None = None) -> dict[str, Any]:
    latest_audit = audit_events[-1].to_dict() if audit_events else None
    return {
        **case.to_record(),
        "status_label": humanize(case.status.value),
        "document_count": len(case.submitted_documents),
        "policy_tag_count": len(case.policy_tags),
        "citation_count": len(case.citations),
        "latest_audit_event": latest_audit,
        "risk_posture": {
            CaseStatus.INTAKE_SUBMITTED: "intake",
            CaseStatus.IN_REVIEW: "in_review",
            CaseStatus.AWAITING_HUMAN_APPROVAL: "needs_approval",
            CaseStatus.APPROVED: "approved",
            CaseStatus.REJECTED: "rejected",
            CaseStatus.ESCALATED: "escalated",
        }[case.status],
    }


def audit_event_to_payload(event: AuditEvent) -> dict[str, Any]:
    payload = event.to_dict()
    payload["summary"] = {
        "case_created": f"Case {event.entity_id} was created.",
        "case_status_changed": f"Case {event.entity_id} changed state.",
        "ai_recommendation_captured": f"AI recommendation captured for {event.entity_id}.",
        "workflow_registered": f"Workflow {event.entity_id} was registered.",
    }[event.action.value]
    return payload


def dashboard_payload() -> dict[str, Any]:
    service = get_demo_service()
    admin, reviewer = _demo_principals()
    workflows = service.list_workflows(admin)
    cases = service.list_cases(admin)
    pending_approvals = service.list_pending_approvals(reviewer)
    recent_case_id = pending_approvals[0].case_id if pending_approvals else cases[0].case_id
    recent_audit_events = service.get_case_audit_trail(admin, recent_case_id)

    status_counts = {status.value: 0 for status in CaseStatus}
    for case in cases:
        status_counts[case.status.value] += 1

    workflow_cards = [workflow_to_payload(workflow) for workflow in workflows]
    case_cards = [
        case_to_payload(case, service.get_case_audit_trail(admin, case.case_id)) for case in cases
    ]
    timeline = [audit_event_to_payload(event) for event in recent_audit_events]

    return {
        "product": "RegFlow AI",
        "service": "control-plane",
        "headline": "AI workflow automation for regulated operations",
        "metrics": {
            "total_workflows": len(workflows),
            "total_cases": len(cases),
            "pending_reviews": len(pending_approvals),
            "approved_cases": status_counts[CaseStatus.APPROVED.value],
            "escalated_cases": status_counts[CaseStatus.ESCALATED.value],
        },
        "status_breakdown": status_counts,
        "workflows": workflow_cards,
        "cases": case_cards,
        "pending_approvals": [case_to_payload(case, service.get_case_audit_trail(admin, case.case_id)) for case in pending_approvals],
        "recent_audit_events": timeline,
        "focus_case_id": recent_case_id,
        "generated_at": timeline[-1]["occurred_at"] if timeline else None,
    }


def case_detail_payload(case_id: str) -> dict[str, Any]:
    service = get_demo_service()
    admin, _ = _demo_principals()
    case = service.get_case(admin, case_id)
    audit_events = service.get_case_audit_trail(admin, case_id)
    return {
        "case": case_to_payload(case, audit_events),
        "audit_timeline": [audit_event_to_payload(event) for event in audit_events],
    }
