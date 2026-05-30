from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.access import AccessControl, Action, UserPrincipal
from app.domain import ActorType, AuditAction, AuditEvent, CaseRecord, CaseStatus, RecommendationOutcome, WorkflowTemplate
from app.repository import RegFlowRepository


@dataclass(slots=True)
class RegFlowService:
    repository: RegFlowRepository
    access_control: AccessControl = field(default_factory=AccessControl)

    def register_workflow(self, actor: UserPrincipal, workflow: WorkflowTemplate) -> WorkflowTemplate:
        self.access_control.require(actor, Action.MANAGE_WORKFLOWS)
        self.repository.save_workflow(workflow)
        self.repository.save_audit_event(
            AuditEvent.for_workflow_registered(
                event_id=f"evt-{uuid4().hex}",
                workflow_id=workflow.workflow_id,
                actor_id=actor.user_id,
                actor_type=ActorType.HUMAN_REVIEWER,
                workflow_name=workflow.name,
            )
        )
        return workflow

    def list_workflows(self, actor: UserPrincipal) -> list[WorkflowTemplate]:
        self.access_control.require(actor, Action.READ_CASES)
        return self.repository.list_workflows()

    def create_case(
        self,
        actor: UserPrincipal,
        case_id: str,
        workflow_id: str,
        applicant_name: str,
        submitted_documents: list[str],
        policy_tags: list[str],
    ) -> CaseRecord:
        self.access_control.require(actor, Action.CREATE_CASES)
        case = CaseRecord.from_intake(
            case_id=case_id,
            workflow_id=workflow_id,
            applicant_name=applicant_name,
            submitted_documents=submitted_documents,
            policy_tags=policy_tags,
        )
        self.repository.save_case(case)
        self.repository.save_audit_event(
            AuditEvent.for_case_created(
                event_id=f"evt-{uuid4().hex}",
                case_id=case.case_id,
                actor_id=actor.user_id,
                actor_type=ActorType.HUMAN_REVIEWER,
                workflow_id=workflow_id,
            )
        )
        return case

    def get_case(self, actor: UserPrincipal, case_id: str) -> CaseRecord:
        self.access_control.require(actor, Action.READ_CASES)
        case = self.repository.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        return case

    def list_cases(self, actor: UserPrincipal) -> list[CaseRecord]:
        self.access_control.require(actor, Action.READ_CASES)
        return self.repository.list_cases()

    def start_ai_review(self, actor: UserPrincipal, case_id: str) -> CaseRecord:
        self.access_control.require(actor, Action.REVIEW_CASES)
        case = self.get_case(actor, case_id)
        case.start_ai_review()
        self.repository.save_case(case)
        return case

    def record_ai_recommendation(
        self,
        actor: UserPrincipal,
        case_id: str,
        outcome: RecommendationOutcome,
        summary: str,
        citations: list[dict[str, str]],
    ) -> CaseRecord:
        self.access_control.require(actor, Action.REVIEW_CASES)
        case = self.get_case(actor, case_id)
        case.attach_ai_recommendation(outcome=outcome, summary=summary, citations=citations)
        self.repository.save_case(case)
        self.repository.save_audit_event(
            AuditEvent(
                event_id=f"evt-{uuid4().hex}",
                entity_type="case",
                entity_id=case.case_id,
                action=AuditAction.AI_RECOMMENDATION_CAPTURED,
                actor_id=actor.user_id,
                actor_type=ActorType.AI_AGENT,
                occurred_at=datetime.now(UTC),
                details={"outcome": outcome.value, "summary": summary},
            )
        )
        return case

    def list_pending_approvals(self, actor: UserPrincipal) -> list[CaseRecord]:
        self.access_control.require(actor, Action.REVIEW_CASES)
        return self.repository.list_cases(status=CaseStatus.AWAITING_HUMAN_APPROVAL)

    def resolve_case(
        self,
        actor: UserPrincipal,
        case_id: str,
        final_status: CaseStatus,
        reviewer_comment: str,
    ) -> CaseRecord:
        self.access_control.require(actor, Action.RESOLVE_CASES)
        case = self.get_case(actor, case_id)
        previous_status = case.status
        case.resolve(
            final_status=final_status,
            reviewer_id=actor.user_id,
            reviewer_comment=reviewer_comment,
        )
        self.repository.save_case(case)
        self.repository.save_audit_event(
            AuditEvent.for_case_status_change(
                event_id=f"evt-{uuid4().hex}",
                case_id=case.case_id,
                actor_id=actor.user_id,
                actor_type=ActorType.HUMAN_REVIEWER,
                from_status=previous_status,
                to_status=final_status,
                comment=reviewer_comment,
            )
        )
        return case

    def get_case_audit_trail(self, actor: UserPrincipal, case_id: str) -> list[AuditEvent]:
        self.access_control.require(actor, Action.READ_AUDIT_TRAIL)
        return self.repository.list_audit_events_for_case(case_id)
