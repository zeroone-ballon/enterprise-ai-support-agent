"""Application configuration with safe, API-key-free defaults."""

import os
from dataclasses import dataclass, field
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
    reviewer_api_key_sha256: str = (
        "2636892cb3695595303bfee4a077276f34a1f9be4a2879257bc4111b5ecc37c0"
    )
    reviewer_actor: str = "service-desk-lead"
    executor_api_key_sha256: str = (
        "8a059a3e30ba84bd7b957c156d42b3e4cb5d61bf5712de83ebdd956c06e1204a"
    )
    executor_actor: str = "automation-operator"
    auditor_api_key_sha256: str = "46151c35c1c09bca0b049ce55099e4f67fd04efe91716eec70fd1fa8ce898163"
    auditor_actor: str = "audit-reader"
    generation_mode: str = "deterministic"
    llm_base_url: str = ""
    llm_api_key: str = field(default="", repr=False)
    llm_model: str = ""
    llm_timeout_seconds: float = 20.0
    execution_mode: str = "sandbox"
    servicenow_instance_url: str = ""
    servicenow_username: str = ""
    servicenow_password: str = field(default="", repr=False)
    servicenow_timeout_seconds: float = 10.0

    def validate_for_startup(self) -> None:
        """Reject insecure production settings while preserving local demo defaults."""

        if self.app_env.casefold() == "production":
            development_digests = {
                type(self)().reviewer_api_key_sha256,
                type(self)().executor_api_key_sha256,
                type(self)().auditor_api_key_sha256,
            }
            configured = {
                self.reviewer_api_key_sha256,
                self.executor_api_key_sha256,
                self.auditor_api_key_sha256,
            }
            if configured & development_digests:
                raise ValueError("development API-key digests are forbidden in production")

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
            lifecycle_db_path=Path(os.getenv("LIFECYCLE_DB_PATH", defaults.lifecycle_db_path)),
            reviewer_api_key_sha256=os.getenv(
                "REVIEWER_API_KEY_SHA256", defaults.reviewer_api_key_sha256
            ),
            reviewer_actor=os.getenv("REVIEWER_ACTOR", defaults.reviewer_actor),
            executor_api_key_sha256=os.getenv(
                "EXECUTOR_API_KEY_SHA256", defaults.executor_api_key_sha256
            ),
            executor_actor=os.getenv("EXECUTOR_ACTOR", defaults.executor_actor),
            auditor_api_key_sha256=os.getenv(
                "AUDITOR_API_KEY_SHA256", defaults.auditor_api_key_sha256
            ),
            auditor_actor=os.getenv("AUDITOR_ACTOR", defaults.auditor_actor),
            generation_mode=os.getenv("GENERATION_MODE", defaults.generation_mode).casefold(),
            llm_base_url=os.getenv("LLM_BASE_URL", defaults.llm_base_url),
            llm_api_key=os.getenv("LLM_API_KEY", defaults.llm_api_key),
            llm_model=os.getenv("LLM_MODEL", defaults.llm_model),
            llm_timeout_seconds=float(
                os.getenv("LLM_TIMEOUT_SECONDS", defaults.llm_timeout_seconds)
            ),
            execution_mode=os.getenv("EXECUTION_MODE", defaults.execution_mode).casefold(),
            servicenow_instance_url=os.getenv(
                "SERVICENOW_INSTANCE_URL", defaults.servicenow_instance_url
            ),
            servicenow_username=os.getenv("SERVICENOW_USERNAME", defaults.servicenow_username),
            servicenow_password=os.getenv("SERVICENOW_PASSWORD", defaults.servicenow_password),
            servicenow_timeout_seconds=float(
                os.getenv("SERVICENOW_TIMEOUT_SECONDS", defaults.servicenow_timeout_seconds)
            ),
        )
