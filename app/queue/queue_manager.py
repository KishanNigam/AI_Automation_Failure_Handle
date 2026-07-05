from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.queue.models import FailureRecord
from app.queue.storage import QueueStorage

logger = logging.getLogger(__name__)


class QueueManager:
    """Manage a bounded in-memory failure queue with persistence."""

    def __init__(self, storage_path: str | None = None, max_size: int = 20) -> None:
        self.storage = QueueStorage(storage_path)
        self.max_size = max_size
        self._failures: list[FailureRecord] = []
        self.load()

    def add_failure(
        self,
        *,
        job_name: str,
        environment: str,
        server: str,
        subject: str,
        received_time: str,
        root_cause: str,
        analysis: Optional[dict[str, Any]] = None,
        email: Optional[dict[str, Any]] = None,
        visualcron_log: Optional[str] = None,
        batch_log: Optional[str] = None,
        vbs_log: Optional[str] = None,
    ) -> FailureRecord:
        fingerprint = FailureRecord.create(
            job_name=job_name,
            environment=environment,
            server=server,
            subject=subject,
            received_time=received_time,
            root_cause=root_cause,
        ).fingerprint

        existing = self.get_by_fingerprint(fingerprint)
        if existing is not None:
            existing.occurrence_count += 1
            existing.last_updated = self._timestamp()
            logger.info("Duplicate failure detected for fingerprint %s", fingerprint)
            self.save()
            return existing

        record = FailureRecord.create(
            job_name=job_name,
            environment=environment,
            server=server,
            subject=subject,
            received_time=received_time,
            root_cause=root_cause,
        )
        record.analysis = analysis
        record.email = email
        record.visualcron_log = visualcron_log
        record.batch_log = batch_log
        record.vbs_log = vbs_log

        self._failures.append(record)
        self._trim_if_needed()
        self.save()
        logger.info("Added new failure %s", record.id)
        return record

    def list_failures(self) -> list[FailureRecord]:
        return list(self._failures)

    def get_failure(self, failure_id: str) -> Optional[FailureRecord]:
        for record in self._failures:
            if record.id == failure_id:
                return record
        return None

    def get_by_fingerprint(self, fingerprint: str) -> Optional[FailureRecord]:
        for record in self._failures:
            if record.fingerprint == fingerprint:
                return record
        return None

    def approve(self, failure_id: str) -> Optional[FailureRecord]:
        record = self.get_failure(failure_id)
        if record is None:
            return None
        record.status = "APPROVED"
        record.last_updated = self._timestamp()
        self.save()
        logger.info("Approved failure %s", failure_id)
        return record

    def reject(self, failure_id: str) -> Optional[FailureRecord]:
        record = self.get_failure(failure_id)
        if record is None:
            return None
        record.status = "REJECTED"
        record.last_updated = self._timestamp()
        self.save()
        logger.info("Rejected failure %s", failure_id)
        return record

    def reset(self) -> None:
        self._failures = []
        self.save()
        logger.info("Queue reset")

    def mark_sent(self, failure_id: str) -> Optional[FailureRecord]:
        record = self.get_failure(failure_id)
        if record is None:
            return None
        record.status = "SENT"
        record.last_updated = self._timestamp()
        self.save()
        logger.info("Marked failure %s as sent", failure_id)
        return record

    def refresh(self) -> None:
        self.load()
        logger.info("Queue refreshed")

    def save(self) -> None:
        payload = [self._serialize(record) for record in self._failures]
        self.storage.save(payload)

    def load(self) -> None:
        self._failures = []
        for item in self.storage.load():
            self._failures.append(self._deserialize(item))

    def _trim_if_needed(self) -> None:
        while len(self._failures) > self.max_size:
            oldest = self._failures.pop(0)
            logger.info("Removed oldest failure %s from queue", oldest.id)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _serialize(record: FailureRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "fingerprint": record.fingerprint,
            "job_name": record.job_name,
            "environment": record.environment,
            "server": record.server,
            "subject": record.subject,
            "received_time": record.received_time,
            "status": record.status,
            "occurrence_count": record.occurrence_count,
            "analysis": record.analysis,
            "email": record.email,
            "visualcron_log": record.visualcron_log,
            "batch_log": record.batch_log,
            "vbs_log": record.vbs_log,
            "created_at": record.created_at,
            "last_updated": record.last_updated,
        }

    @staticmethod
    def _deserialize(payload: dict[str, Any]) -> FailureRecord:
        return FailureRecord(
            id=str(payload["id"]),
            fingerprint=str(payload["fingerprint"]),
            job_name=str(payload.get("job_name", "")),
            environment=str(payload.get("environment", "")),
            server=str(payload.get("server", "")),
            subject=str(payload.get("subject", "")),
            received_time=str(payload.get("received_time", "")),
            status=str(payload.get("status", "NEW")),
            occurrence_count=int(payload.get("occurrence_count", 1)),
            analysis=payload.get("analysis"),
            email=payload.get("email"),
            visualcron_log=payload.get("visualcron_log"),
            batch_log=payload.get("batch_log"),
            vbs_log=payload.get("vbs_log"),
            created_at=str(payload.get("created_at", "")),
            last_updated=str(payload.get("last_updated", "")),
        )
