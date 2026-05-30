import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from app.main import app, healthcheck, root_metadata


class ApiMainTests(unittest.TestCase):
    def test_health_endpoint_reports_service_is_ok(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                healthcheck(),
                {
                    "service": "regflow-api",
                    "status": "ok",
                    "environment": "development",
                    "database_engine": "sqlite",
                },
            )

    def test_root_endpoint_returns_product_metadata(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgresql://regflow:***@postgres:5432/regflow"},
            clear=True,
        ):
            payload = root_metadata()

        self.assertEqual(payload["product"], "RegFlow AI")
        self.assertEqual(payload["service"], "control-plane")
        self.assertIn("auditability", payload["capabilities"])
        self.assertEqual(payload["database_engine"], "postgres")
        self.assertEqual(
            payload["database_bootstrap_path"],
            str(Path(__file__).resolve().parents[2] / "infra" / "docker" / "init" / "001-regflow-schema.sql"),
        )

    def test_dashboard_endpoint_returns_seeded_snapshot(self) -> None:
        client = TestClient(app)

        response = client.get("/api/dashboard")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["product"], "RegFlow AI")
        self.assertGreaterEqual(payload["metrics"]["total_cases"], 1)
        self.assertGreaterEqual(payload["metrics"]["pending_reviews"], 1)
        self.assertGreaterEqual(len(payload["workflows"]), 1)
        self.assertGreaterEqual(len(payload["cases"]), 1)
        self.assertGreaterEqual(len(payload["pending_approvals"]), 1)
        self.assertGreaterEqual(len(payload["recent_audit_events"]), 1)

    def test_case_audit_endpoint_returns_timeline(self) -> None:
        client = TestClient(app)

        response = client.get("/api/cases/case-001/audit")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["events"]), 1)
        self.assertEqual(payload["case_id"], "case-001")

    def test_case_recommendation_endpoint_returns_grounded_evidence(self) -> None:
        client = TestClient(app)

        response = client.get("/api/cases/case-001/recommendation")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["case_id"], "case-001")
        self.assertGreaterEqual(payload["recommendation"]["confidence"], 0.4)
        self.assertGreaterEqual(len(payload["recommendation"]["retrieved_chunks"]), 1)
        self.assertGreaterEqual(len(payload["recommendation"]["citations"]), 1)


if __name__ == "__main__":
    unittest.main()
