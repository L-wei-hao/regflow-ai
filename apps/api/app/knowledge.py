from __future__ import annotations

from typing import Any

from app.domain import CaseRecord, RecommendationOutcome
from app.policy_corpus import DEFAULT_POLICY_DIR, PolicyChunk, build_policy_corpus


def _normalize_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for token in value.lower().replace("/", " ").replace("-", " ").replace("_", " ").replace(".", " ").split():
            cleaned = "".join(char for char in token if char.isalnum())
            if cleaned:
                tokens.add(cleaned)
    return tokens


def _match_terms(*groups: set[str]) -> list[str]:
    matched: set[str] = set()
    for group in groups:
        matched.update(group)
    return sorted(matched)


def _score_chunk(query_tokens: set[str], document_tokens: set[str], chunk: PolicyChunk, index: int) -> tuple[int, list[str]]:
    chunk_tokens = _normalize_tokens(chunk.source, chunk.title, chunk.section, chunk.excerpt, " ".join(chunk.tags), " ".join(chunk.keywords))
    tag_overlap = query_tokens.intersection(_normalize_tokens(" ".join(chunk.tags)))
    keyword_overlap = query_tokens.intersection(_normalize_tokens(" ".join(chunk.keywords)))
    document_overlap = document_tokens.intersection(chunk_tokens)

    raw_score = len(tag_overlap) * 24 + len(keyword_overlap) * 16 + len(document_overlap) * 12
    if raw_score == 0:
        return 0, []

    score = min(100, raw_score + max(0, 5 - index))
    matched_terms = _match_terms(tag_overlap, keyword_overlap, document_overlap)
    return score, matched_terms


def retrieve_policy_chunks(
    query: str,
    policy_tags: list[str],
    submitted_documents: list[str],
    limit: int = 3,
    policy_dir: str | None = None,
) -> list[dict[str, Any]]:
    corpus = build_policy_corpus(policy_dir or DEFAULT_POLICY_DIR)
    query_tokens = _normalize_tokens(query, " ".join(policy_tags), " ".join(submitted_documents))
    document_tokens = _normalize_tokens(" ".join(submitted_documents))

    scored_chunks: list[dict[str, Any]] = []
    for index, chunk in enumerate(corpus):
        score, matched_terms = _score_chunk(query_tokens, document_tokens, chunk, index)
        if score == 0:
            continue
        scored_chunks.append(
            {
                "source": chunk.source,
                "title": chunk.title,
                "section": chunk.section,
                "excerpt": chunk.excerpt,
                "recommended_outcome": chunk.recommended_outcome.value,
                "escalation_required": chunk.escalation_required,
                "score": score,
                "matched_terms": matched_terms,
            }
        )

    scored_chunks.sort(key=lambda item: (-item["score"], item["source"], item["title"], item["section"]))
    return scored_chunks[:limit]


def build_case_recommendation(case: CaseRecord, policy_dir: str | None = None) -> dict[str, Any]:
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
    retrieved_chunks = retrieve_policy_chunks(query, case.policy_tags, case.submitted_documents, limit=3, policy_dir=policy_dir)
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
            "section": chunk["section"],
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
