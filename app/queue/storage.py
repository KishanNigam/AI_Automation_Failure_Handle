from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class QueueStorage:
    """Persist and load in-memory queue state to queue.json."""

    def __init__(self, storage_path: str | None = None) -> None:
        self.storage_path = Path(storage_path or "queue.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, payload: list[dict[str, Any]]) -> None:
        try:
            self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.info("Queue state saved to %s", self.storage_path)
        except Exception as exc:
            logger.exception("Failed to save queue state")
            raise RuntimeError("Unable to save queue state") from exc

    def load(self) -> list[dict[str, Any]]:
        if not self.storage_path.exists():
            return []

        try:
            content = self.storage_path.read_text(encoding="utf-8")
            if not content.strip():
                return []
            payload = json.loads(content)
            if not isinstance(payload, list):
                raise ValueError("Queue storage must contain a JSON array")
            logger.info("Queue state loaded from %s", self.storage_path)
            return payload
        except Exception as exc:
            logger.exception("Failed to load queue state")
            raise RuntimeError("Unable to load queue state") from exc
