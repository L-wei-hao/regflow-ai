from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.demo import case_detail_payload, dashboard_payload
from app.repository import DatabaseConfig

SERVICE_NAME = "regflow-api"
ENVIRONMENT = "development"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
POSTGRES_BOOTSTRAP_PATH = PROJECT_ROOT / "infra" / "docker" / "init" / "001-regflow-schema.sql"

app = FastAPI(title="RegFlow AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def current_database_config() -> DatabaseConfig:
    return DatabaseConfig.from_env(PROJECT_ROOT)


def healthcheck() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "status": "ok",
        "environment": ENVIRONMENT,
        "database_engine": current_database_config().engine,
    }


def root_metadata() -> dict[str, Any]:
    database_config = current_database_config()
    return {
        "product": "RegFlow AI",
        "service": "control-plane",
        "capabilities": [
            "case-management",
            "workflow-templates",
            "auditability",
            "approvals",
            "postgres-ready-persistence",
        ],
        "database_engine": database_config.engine,
        "database_bootstrap_path": str(POSTGRES_BOOTSTRAP_PATH),
        "next_milestone": "live-dashboard-and-audit-ui",
    }


@app.get("/health")
def health_endpoint() -> dict[str, str]:
    return healthcheck()


@app.get("/")
def root_endpoint() -> dict[str, Any]:
    return root_metadata()


@app.get("/api/dashboard")
def dashboard_endpoint() -> dict[str, Any]:
    return dashboard_payload()


@app.get("/api/workflows")
def workflows_endpoint() -> dict[str, Any]:
    payload = dashboard_payload()
    return {
        "workflows": payload["workflows"],
        "metrics": payload["metrics"],
    }


@app.get("/api/cases")
def cases_endpoint(status: str | None = Query(default=None)) -> dict[str, Any]:
    payload = dashboard_payload()
    cases = payload["cases"]
    if status:
        cases = [case for case in cases if case["status"] == status]
    return {"cases": cases, "count": len(cases)}


@app.get("/api/cases/{case_id}")
def case_detail_endpoint(case_id: str) -> dict[str, Any]:
    try:
        return case_detail_payload(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"case '{case_id}' not found") from exc


@app.get("/api/cases/{case_id}/audit")
def case_audit_endpoint(case_id: str) -> dict[str, Any]:
    try:
        payload = case_detail_payload(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"case '{case_id}' not found") from exc
    return {
        "case_id": case_id,
        "events": payload["audit_timeline"],
        "case": payload["case"],
    }
