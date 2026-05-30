from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain import CaseRecord, RecommendationOutcome

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class PolicyChunk:
    source: str
    title: str
    excerpt: str
    tags: tuple[str, ...]
    keywords: tuple[str, ...]
    recommended_outcome: RecommendationOutcome
    escalation_required: bool = False


POLICY_LIBRARY: tuple[PolicyChunk, ...] = (
    PolicyChunk(
        source="policy/kyc-standard.md",
        title="Standard KYC onboarding policy",
        excerpt="Approve when identity and address evidence are complete and no escalation flags are present.",
        tags=("kyc", "identity", "proof-of-address", "low-risk"),
        keywords=("passport", "proof-of-address", "utility bill", "salary slip", "complete"),
        recommended_outcome=RecommendationOutcome.APPROVE,
    ),
    PolicyChunk(
        source="policy/kyc-standard.md",
        title="Standard KYC income verification",
        excerpt="Incomplete income evidence should be routed to human approval before onboarding.",
        tags=("kyc", "income", "proof-of-funds", "review"),
        keywords=("income", "salary slip", "proof-of-income", "manual confirmation"),
        recommended_outcome=RecommendationOutcome.NEEDS_HUMAN_REVIEW,
        escalation_required=True,
    ),
    PolicyChunk(
        source="policy/sanctions-escalation.md",
        title="Sanctions escalation workflow",
        excerpt="Potential sanctions matches must be escalated to the review board with supporting context.",
        tags=("sanctions", "trade-finance", "escalation", "review-board"),
        keywords=("sanctions", "screening", "beneficial owner", "review board", "match"),
        recommended_outcome=RecommendationOutcome.ESCALATE,
        escalation_required=True,
    ),
    PolicyChunk(
        source="policy/enhanced-due-diligence.md",
        title="Enhanced due diligence standard",
        excerpt="Cases with incomplete source-of-funds evidence should remain in human review until supporting documents are verified.",
        tags=("edd", "source-of-funds", "high-risk", "review"),
        keywords=("source of funds", "supporting documents", "high risk", "verification"),
        recommended_outcome=RecommendationOutcome.NEEDS_HUMAN_REVIEW,
        escalation_required=True,
    ),
)


def _normalize_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        tokens.update(_WORD_RE.findall(value.lower()))
    return tokens


def retrieve_policy_chunks(
    query: str,
    policy_tags: list[str],
    submitted_documents: list[str],
    limit: int = 3,
) -> list[dict[str, Any]]:
    query_tokens = _normalize_tokens(query, " ".join(policy_tags), " ".join(submitted_documents))
    document_tokens = _normalize_tokens(" ".join(submitted_documents))
    tag_tokens = _normalize_tokens(" ".join(policy_tags))

    scored_chunks: list[dict[str, Any]] = []
    for index, chunk in enumerate(POLICY_LIBRARY):
        chunk_tokens = _normalize_tokens(chunk.source, chunk.title, chunk.excerpt, " ".join(chunk.tags), " ".join(chunk.keywords))
        tag_overlap = query_tokens.intersection(_normalize_tokens(" ".join(chunk.tags)))
        keyword_overlap = query_tokens.intersection(_normalize_tokens(" ".join(chunk.keywords)))
        document_overlap = document_tokens.intersection(chunk_tokens)
        policy_tag_overlap = tag_tokens.intersection(chunk_tokens)

        raw_score = (
            len(tag_overlap) * 24
            + len(keyword_overlap) * 16
            + len(document_overlap) * 14
            + len(policy_tag_overlap) * 10
        )

        if raw_score == 0:
            continue

        matched_terms = sorted(tag_overlap.union(keyword_overlap).union(document_overlap).union(policy_tag_overlap))
        scored_chunks.append(
            {
                "source": chunk.source,
                "title": chunk.title,
                "excerpt": chunk.excerpt,
                "recommended_outcome": chunk.recommended_outcome.value,
                "escalation_required": chunk.escalation_required,
                "score": min(100, raw_score + max(0, 6 - index)),
                "matched_terms": matched_terms,
            }
        )

    scored_chunks.sort(key=lambda item: (-item["score"], item["source"], item["title"]))
    return scored_chunks[:limit]


def build_case_recommendation(case: CaseRecord) -> dict[str, Any]:
    query = " ".join(
        [
            case.case_id,
            case.workflow_id,
            case.applicant_name,
            case.ai_summary or "",
            *case.policy_tags,
            *case.submitted_documents,
        ]
    )
    retrieved_chunks = retrieve_policy_chunks(query, case.policy_tags, case.submitted_documents, limit=3)
    top_chunk = retrieved_chunks[0] if retrieved_chunks else None

    if top_chunk is None:
        return {
            "case_id": case.case_id,
            "question": f"Should {case.applicant_name} be approved under {case.workflow_id}?",
            "outcome": RecommendationOutcome.NEEDS_HUMAN_REVIEW.value,
            "confidence": 0.38,
            "reasoning": "No policy snippets matched strongly enough; route the case to a reviewer.",
            "escalation_required": True,
            "retrieved_chunks": [],
            "citations": [],
        }

    confidence = round(min(0.97, 0.42 + top_chunk["score"] / 140), 2)
    outcome = top_chunk["recommended_outcome"]
    if case.ai_summary and case.ai_summary.strip():
        reasoning = f"The AI summary matches {top_chunk['title'].lower()} and the retrieved evidence supports {outcome.replace('_', ' ')}."
    else:
        reasoning = f"The retrieved evidence from {top_chunk['title']} supports {outcome.replace('_', ' ')}."

    citations = [
        {
            "source": chunk["source"],
            "excerpt": chunk["excerpt"],
        }
        for chunk in retrieved_chunks[:2]
    ]

    return {
        "case_id": case.case_id,
        "question": f"Should {case.applicant_name} be approved under {case.workflow_id}?",
        "outcome": outcome,
        "confidence": confidence,
        "reasoning": reasoning,
        "escalation_required": top_chunk["escalation_required"],
        "retrieved_chunks": retrieved_chunks,
        "citations": citations,
    }
