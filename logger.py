from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from settings import Settings

DEFAULT_FORMAT: Final[str] = "%(asctime)s | %(levelname)s | %(message)s"


def configure_logging(settings: Settings | None = None) -> logging.Logger:
    """Configure console and file logging for the POC."""
    resolved_settings = settings or Settings.load()
    log_path = Path(resolved_settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("visualcron_ai_agent")
    logger.setLevel(getattr(logging, resolved_settings.log_level.upper(), logging.INFO))
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
