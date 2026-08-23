"""Application configuration with safe, API-key-free defaults."""

import os
from dataclasses import dataclass

from support_agent import __version__


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings read from environment variables."""

    app_name: str = "Enterprise AI Support Agent"
    app_env: str = "development"
    app_version: str = __version__
    log_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings without requiring a dotenv dependency or secrets."""

        defaults = cls()
        return cls(
            app_name=os.getenv("APP_NAME", defaults.app_name),
            app_env=os.getenv("APP_ENV", defaults.app_env),
            app_version=os.getenv("APP_VERSION", defaults.app_version),
            log_level=os.getenv("LOG_LEVEL", defaults.log_level).upper(),
        )
