"""Application configuration with safe, API-key-free defaults."""

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from support_agent import __version__


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings read from environment variables."""

    app_name: str = "Enterprise AI Support Agent"
    app_env: str = "development"
    app_version: str = __version__
    log_level: str = "INFO"
    knowledge_path: Path = Path(__file__).resolve().parents[2] / "data" / "knowledge.json"
    freshness_reference_date: date = date(2026, 8, 23)
    freshness_max_age_days: int = 365
    lifecycle_db_path: Path = Path(__file__).resolve().parents[2] / "data" / "support_agent.db"
    reviewer_api_key: str = "dev-reviewer-key"
    reviewer_actor: str = "service-desk-lead"
    executor_api_key: str = "dev-executor-key"
    executor_actor: str = "automation-operator"
    auditor_api_key: str = "dev-auditor-key"
    auditor_actor: str = "audit-reader"

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings without requiring a dotenv dependency or secrets."""

        defaults = cls()
        return cls(
            app_name=os.getenv("APP_NAME", defaults.app_name),
            app_env=os.getenv("APP_ENV", defaults.app_env),
            app_version=os.getenv("APP_VERSION", defaults.app_version),
            log_level=os.getenv("LOG_LEVEL", defaults.log_level).upper(),
            knowledge_path=Path(os.getenv("KNOWLEDGE_PATH", defaults.knowledge_path)),
            freshness_reference_date=date.fromisoformat(
                os.getenv(
                    "FRESHNESS_REFERENCE_DATE",
                    defaults.freshness_reference_date.isoformat(),
                )
            ),
            freshness_max_age_days=int(
                os.getenv("FRESHNESS_MAX_AGE_DAYS", defaults.freshness_max_age_days)
            ),
            lifecycle_db_path=Path(
                os.getenv("LIFECYCLE_DB_PATH", defaults.lifecycle_db_path)
            ),
            reviewer_api_key=os.getenv("REVIEWER_API_KEY", defaults.reviewer_api_key),
            reviewer_actor=os.getenv("REVIEWER_ACTOR", defaults.reviewer_actor),
            executor_api_key=os.getenv("EXECUTOR_API_KEY", defaults.executor_api_key),
            executor_actor=os.getenv("EXECUTOR_ACTOR", defaults.executor_actor),
            auditor_api_key=os.getenv("AUDITOR_API_KEY", defaults.auditor_api_key),
            auditor_actor=os.getenv("AUDITOR_ACTOR", defaults.auditor_actor),
        )
