from __future__ import annotations

import os
from pathlib import Path
from typing import Final

BASE_DIR: Final[Path] = Path(__file__).resolve().parent
ENV_FILE: Final[Path] = BASE_DIR / ".env"


def get_env(name: str, default: str | None = None) -> str | None:
    """Return an environment variable value."""
    return os.getenv(name, default)
