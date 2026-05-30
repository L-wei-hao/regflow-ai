import unittest

from app.main import generate_recommendation, healthcheck


class AiOrchestratorTests(unittest.TestCase):
    def test_health_endpoint_reports_orchestrator_status(self) -> None:
        self.assertEqual(
            healthcheck(),
            {
                "service": "regflow-ai-orchestrator",
                "status": "ok",
                "environment": "development",
            },
        )

    def test_recommendation_endpoint_returns_grounded_response_shape(self) -> None:
        payload = {
            "case_id": "case-001",
            "question": "Should we approve this onboarding case?",
            "retrieved_chunks": [
                {
                    "source": "policy.md",
                    "excerpt": "Escalate when proof of address is missing.",
                }
            ],
        }

        body = generate_recommendation(payload)

        self.assertEqual(body["case_id"], "case-001")
        self.assertEqual(body["outcome"], "needs_human_review")
        self.assertEqual(body["citations"][0]["source"], "policy.md")
        self.assertIn("reasoning", body)


if __name__ == "__main__":
    unittest.main()
