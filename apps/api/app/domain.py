from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class CaseStatus(str, Enum):
    INTAKE_SUBMITTED = "intake_submitted"
    IN_REVIEW = "in_review"
    AWAITING_HUMAN_APPROVAL = "awaiting_human_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class RecommendationOutcome(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    ESCALATE = "escalate"


class WorkflowStepType(str, Enum):
    DOCUMENT_COLLECTION = "document_collection"
    POLICY_RETRIEVAL = "policy_retrieval"
    AI_RECOMMENDATION = "ai_recommendation"
    HUMAN_APPROVAL = "human_approval"
    FINAL_DECISION = "final_decision"


class ActorType(str, Enum):
    SYSTEM = "system"
    HUMAN_REVIEWER = "human_reviewer"
    AI_AGENT = "ai_agent"


class AuditAction(str, Enum):
    CASE_STATUS_CHANGED = "case_status_changed"
    AI_RECOMMENDATION_CAPTURED = "ai_recommendation_captured"
    WORKFLOW_REGISTERED = "workflow_registered"


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    step_id: str
    name: str
    step_type: WorkflowStepType

    def is_blocking(self) -> bool:
        return self.step_type in {
            WorkflowStepType.HUMAN_APPROVAL,
            WorkflowStepType.FINAL_DECISION,
        }

    def to_dict(self) -> dict[str, str]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "step_type": self.step_type.value,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "WorkflowStep":
        return cls(
            step_id=payload["step_id"],
            name=payload["name"],
            step_type=WorkflowStepType(payload["step_type"]),
        )


@dataclass(slots=True)
class WorkflowTemplate:
    workflow_id: str
    name: str
    version: str
    steps: list[WorkflowStep]
    regulated: bool = True

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("workflow must define at least one step")

        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("workflow step ids must be unique")

        if self.regulated and not any(
            step.step_type == WorkflowStepType.HUMAN_APPROVAL for step in self.steps
        ):
            raise ValueError("regulated workflows must include a human approval step")

    def blocking_step_ids(self) -> list[str]:
        return [step.step_id for step in self.steps if step.is_blocking()]

    def to_record(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "version": self.version,
            "regulated": self.regulated,
        }


@dataclass(slots=True)
class CaseRecord:
    case_id: str
    workflow_id: str
    applicant_name: str
    submitted_documents: list[str]
    policy_tags: list[str]
    status: CaseStatus = CaseStatus.INTAKE_SUBMITTED
    ai_outcome: RecommendationOutcome | None = None
    ai_summary: str | None = None
    citations: list[dict[str, str]] = field(default_factory=list)
    assigned_reviewer: str | None = None
    reviewer_comment: str | None = None

    @classmethod
    def from_intake(
        cls,
        case_id: str,
        workflow_id: str,
        applicant_name: str,
        submitted_documents: list[str],
        policy_tags: list[str],
    ) -> "CaseRecord":
        if not submitted_documents:
            raise ValueError("at least one supporting document is required")

        return cls(
            case_id=case_id,
            workflow_id=workflow_id,
            applicant_name=applicant_name,
            submitted_documents=list(submitted_documents),
            policy_tags=list(policy_tags),
        )

    def start_ai_review(self) -> None:
        if self.status != CaseStatus.INTAKE_SUBMITTED:
            raise ValueError("case can only enter AI review from intake_submitted")
        self.status = CaseStatus.IN_REVIEW

    def attach_ai_recommendation(
        self,
        outcome: RecommendationOutcome,
        summary: str,
        citations: list[dict[str, str]],
    ) -> None:
        if self.status != CaseStatus.IN_REVIEW:
            raise ValueError("case must be in review before an AI recommendation is attached")
        if not summary.strip():
            raise ValueError("ai recommendation summary cannot be empty")

        self.ai_outcome = outcome
        self.ai_summary = summary
        self.citations = list(citations)
        self.status = CaseStatus.AWAITING_HUMAN_APPROVAL

    def resolve(
        self,
        final_status: CaseStatus,
        reviewer_id: str,
        reviewer_comment: str,
    ) -> None:
        if self.status != CaseStatus.AWAITING_HUMAN_APPROVAL:
            raise ValueError("case must be awaiting human approval before resolution")
        if final_status not in {
            CaseStatus.APPROVED,
            CaseStatus.REJECTED,
            CaseStatus.ESCALATED,
        }:
            raise ValueError("final case status must be approved, rejected, or escalated")

        self.status = final_status
        self.assigned_reviewer = reviewer_id
        self.reviewer_comment = reviewer_comment

    def to_record(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "workflow_id": self.workflow_id,
            "applicant_name": self.applicant_name,
            "submitted_documents": self.submitted_documents,
            "policy_tags": self.policy_tags,
            "status": self.status.value,
            "ai_outcome": self.ai_outcome.value if self.ai_outcome else None,
            "ai_summary": self.ai_summary,
            "citations": self.citations,
            "assigned_reviewer": self.assigned_reviewer,
            "reviewer_comment": self.reviewer_comment,
        }

    @classmethod
    def from_record(cls, payload: dict[str, Any]) -> "CaseRecord":
        return cls(
            case_id=payload["case_id"],
            workflow_id=payload["workflow_id"],
            applicant_name=payload["applicant_name"],
            submitted_documents=list(payload["submitted_documents"]),
            policy_tags=list(payload["policy_tags"]),
            status=CaseStatus(payload["status"]),
            ai_outcome=(RecommendationOutcome(payload["ai_outcome"]) if payload["ai_outcome"] else None),
            ai_summary=payload["ai_summary"],
            citations=list(payload["citations"]),
            assigned_reviewer=payload["assigned_reviewer"],
            reviewer_comment=payload["reviewer_comment"],
        )


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    entity_type: str
    entity_id: str
    action: AuditAction
    actor_id: str
    actor_type: ActorType
    occurred_at: datetime
    details: dict[str, Any]

    @classmethod
    def for_case_status_change(
        cls,
        event_id: str,
        case_id: str,
        actor_id: str,
        actor_type: ActorType,
        from_status: CaseStatus,
        to_status: CaseStatus,
        comment: str,
    ) -> "AuditEvent":
        return cls(
            event_id=event_id,
            entity_type="case",
            entity_id=case_id,
            action=AuditAction.CASE_STATUS_CHANGED,
            actor_id=actor_id,
            actor_type=actor_type,
            occurred_at=datetime.now(UTC),
            details={
                "from_status": from_status.value,
                "to_status": to_status.value,
                "comment": comment,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action.value,
            "occurred_at": self.occurred_at.isoformat(),
            "actor": {
                "id": self.actor_id,
                "type": self.actor_type.value,
            },
            "details": self.details,
        }

    @classmethod
    def from_record(cls, payload: dict[str, Any]) -> "AuditEvent":
        return cls(
            event_id=payload["event_id"],
            entity_type=payload["entity_type"],
            entity_id=payload["entity_id"],
            action=AuditAction(payload["action"]),
            actor_id=payload["actor_id"],
            actor_type=ActorType(payload["actor_type"]),
            occurred_at=datetime.fromisoformat(payload["occurred_at"]),
            details=dict(payload["details"]),
        )
