from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class InvalidFailureEmailFormat(ValueError):
    """Raised when a failure email subject does not follow the expected format."""


@dataclass(slots=True)
class FailureEvent:
    """Structured representation of a VisualCron failure email."""

    job_name: str
    environment: str
    server_name: str
    subject: str
    sender: str | None
    received_time: Any
    body: str | None


def parse_failure_email(email: dict[str, Any]) -> FailureEvent:
    """Parse a failure email dictionary into a FailureEvent object."""
    try:
        subject = str(email.get("subject") or "").strip()
        if not subject:
            raise InvalidFailureEmailFormat("Email subject is empty")

        pattern = re.compile(r"^\[EXTERNAL\] EAS-P5-MW - (.+?) - (.+?) - (.+?)$")
        match = pattern.match(subject)
        if not match:
            raise InvalidFailureEmailFormat(f"Invalid subject format: {subject}")

        job_name, environment, server_name = (part.strip() for part in match.groups())

        return FailureEvent(
            job_name=job_name,
            environment=environment,
            server_name=server_name,
            subject=subject,
            sender=email.get("sender"),
            received_time=email.get("received_time"),
            body=email.get("body"),
        )
    except InvalidFailureEmailFormat:
        logger.exception("Invalid failure email format: %s", subject)
        raise
    except Exception as exc:
        logger.exception("Failed to parse failure email")
        raise RuntimeError("Unable to parse failure email") from exc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    sample_email = {
        "subject": "[EXTERNAL] EAS-P5-MW - BAI2_File_Import - PROD - BHSIEAS32",
        "sender": "VisualCron",
        "received_time": "2026-07-04 00:00:00",
        "body": "Failure details",
    }

    try:
        event = parse_failure_email(sample_email)
        print("====================================")
        print("Failure Event")
        print(f"Job Name: {event.job_name}")
        print(f"Environment: {event.environment}")
        print(f"Server: {event.server_name}")
        print(f"Sender: {event.sender}")
        print(f"Received: {event.received_time}")
        print("====================================")
    except Exception as exc:
        logger.error("Unable to print failure event: %s", exc)
