from __future__ import annotations

from typing import Any

SERVICE_NAME = "regflow-ai-orchestrator"
ENVIRONMENT = "development"


def healthcheck() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "status": "ok",
        "environment": ENVIRONMENT,
    }


def generate_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    retrieved_chunks = payload.get("retrieved_chunks", [])
    first_chunk = retrieved_chunks[0] if retrieved_chunks else {
        "source": "unknown",
        "excerpt": "No supporting policy snippet was provided.",
    }

    return {
        "case_id": payload.get("case_id", "unknown-case"),
        "outcome": "needs_human_review",
        "reasoning": (
            "Initial scaffold defaults high-risk workflow decisions to human review "
            "until confidence scoring and retrieval evaluation are implemented."
        ),
        "citations": [
            {
                "source": first_chunk["source"],
                "excerpt": first_chunk["excerpt"],
            }
        ],
    }
