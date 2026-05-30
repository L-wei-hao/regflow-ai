import unittest

from app.domain import CaseRecord, RecommendationOutcome
from app.knowledge import build_case_recommendation, retrieve_policy_chunks
from app.policy_corpus import policy_corpus_summary


class KnowledgeRetrievalTests(unittest.TestCase):
    def test_retrieves_kyc_policy_support_for_incomplete_income_evidence(self) -> None:
        chunks = retrieve_policy_chunks(
            query="Jane Tan kyc passport utility bill complete address evidence",
            policy_tags=["kyc", "low-risk"],
            submitted_documents=["passport.pdf", "utility_bill.pdf"],
        )

        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["source"], "policy/kyc-standard.md")
        self.assertIn(chunks[0]["section"], {"Overview", "Evidence requirements", "Decision guidance"})
        self.assertGreaterEqual(chunks[0]["score"], 40)

    def test_policy_corpus_summary_counts_documents_and_chunks(self) -> None:
        summary = policy_corpus_summary()

        self.assertGreaterEqual(summary.document_count, 4)
        self.assertGreaterEqual(summary.chunk_count, 4)
        self.assertIn("policy/kyc-standard.md", summary.sources)

    def test_build_case_recommendation_returns_grounded_citations(self) -> None:
        case = CaseRecord.from_intake(
            case_id="case-001",
            workflow_id="kyc-standard",
            applicant_name="Jane Tan",
            submitted_documents=["passport.pdf", "proof-of-address.pdf"],
            policy_tags=["kyc", "proof-of-address"],
        )
        case.start_ai_review()
        case.attach_ai_recommendation(
            outcome=RecommendationOutcome.NEEDS_HUMAN_REVIEW,
            summary="Proof of income needs manual confirmation.",
            citations=[{"source": "policy/kyc-standard.md", "excerpt": "Incomplete income evidence should be routed to human approval before onboarding."}],
        )

        recommendation = build_case_recommendation(case)

        self.assertEqual(recommendation["case_id"], "case-001")
        self.assertGreaterEqual(recommendation["confidence"], 0.4)
        self.assertIn(recommendation["citations"][0]["source"], {"policy/kyc-standard.md", "policy/kyc-income-verification.md"})
        self.assertIn(recommendation["outcome"], {RecommendationOutcome.APPROVE.value, RecommendationOutcome.NEEDS_HUMAN_REVIEW.value})


if __name__ == "__main__":
    unittest.main()
