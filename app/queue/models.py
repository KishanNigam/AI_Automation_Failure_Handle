from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(slots=True)
class FailureRecord:
    id: str
    fingerprint: str
    job_name: str
    environment: str
    server: str
    subject: str
    received_time: str
    status: str = "NEW"
    occurrence_count: int = 1
    analysis: Optional[dict[str, Any]] = None
    email: Optional[dict[str, Any]] = None
    visualcron_log: Optional[str] = None
    batch_log: Optional[str] = None
    vbs_log: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def create(
        cls,
        *,
        job_name: str,
        environment: str,
        server: str,
        subject: str,
        received_time: str,
        root_cause: str,
    ) -> "FailureRecord":
        fingerprint = hashlib.sha256(
            f"{job_name}{environment}{server}{root_cause}".encode("utf-8")
        ).hexdigest()
        return cls(
            id=fingerprint[:12],
            fingerprint=fingerprint,
            job_name=job_name,
            environment=environment,
            server=server,
            subject=subject,
            received_time=received_time,
        )
