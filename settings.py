from __future__ import annotations

from dataclasses import dataclass

from dotenv import load_dotenv

from config import ENV_FILE, get_env


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str
    environment: str
    log_level: str
    log_file: str

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment variables."""
        load_dotenv(ENV_FILE, override=False)
        return cls(
            app_name=get_env("APP_NAME", "visualcron-ai-agent") or "visualcron-ai-agent",
            environment=get_env("ENVIRONMENT", "development") or "development",
            log_level=get_env("LOG_LEVEL", "INFO") or "INFO",
            log_file=get_env("LOG_FILE", "logs/app.log") or "logs/app.log",
        )
