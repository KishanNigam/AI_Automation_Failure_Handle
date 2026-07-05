from __future__ import annotations

import json
import logging
from datetime import datetime
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
            serialized = json.dumps(payload, indent=2, default=self._json_default)
            self.storage_path.write_text(serialized, encoding="utf-8")
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
            payload = json.loads(content, object_hook=self._json_object_hook)
            if not isinstance(payload, list):
                raise ValueError("Queue storage must contain a JSON array")
            logger.info("Queue state loaded from %s", self.storage_path)
            return payload
        except Exception as exc:
            logger.exception("Failed to load queue state")
            raise RuntimeError("Unable to load queue state") from exc

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    @staticmethod
    def _json_object_hook(payload: dict[str, Any]) -> dict[str, Any]:
        converted: dict[str, Any] = {}
        for key, value in payload.items():
            if key in {"received_time", "created_at", "last_updated"} and isinstance(value, str):
                converted[key] = QueueStorage._coerce_datetime(value)
            else:
                converted[key] = value
        return converted

    @staticmethod
    def _coerce_datetime(value: str) -> Any:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return value
