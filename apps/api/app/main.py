from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repository import DatabaseConfig

SERVICE_NAME = "regflow-api"
ENVIRONMENT = "development"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
POSTGRES_BOOTSTRAP_PATH = PROJECT_ROOT / "infra" / "docker" / "init" / "001-regflow-schema.sql"


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
        "next_milestone": "rbac-and-http-api",
    }
