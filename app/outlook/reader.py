from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_inbox() -> Any:
    """Connect to the default Outlook Inbox using the Desktop COM interface."""
    try:
        import win32com.client as win32
    except ImportError as exc:
        raise RuntimeError("pywin32 is required to access Outlook via COM.") from exc

    try:
        outlook = win32.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        return namespace.GetDefaultFolder(6)
    except Exception as exc:
        logger.exception("Failed to connect to Outlook")
        raise RuntimeError("Unable to connect to Microsoft Outlook.") from exc


def get_failure_emails(limit: int = 50) -> list[dict[str, Any]]:
    """Return VisualCron failure emails from the latest emails in the Inbox."""
    if limit <= 0:
        return []

    try:
        inbox = _get_inbox()
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)

        failure_emails: list[dict[str, Any]] = []
        for item in items:
            if len(failure_emails) >= limit:
                break

            try:
                if getattr(item, "Class", None) != 43:
                    continue

                subject = getattr(item, "Subject", "") or ""
                if not subject.startswith("[EXTERNAL] EAS-P5-MW"):
                    continue

                failure_emails.append(
                    {
                        "subject": subject,
                        "sender": getattr(item, "SenderName", None) or getattr(item, "SenderEmailAddress", None),
                        "received_time": getattr(item, "ReceivedTime", None),
                        "body": getattr(item, "Body", None),
                    }
                )
            except Exception as exc:
                logger.exception("Failed to read an Outlook email entry")
                raise RuntimeError("Unable to read one or more Outlook emails.") from exc

        return failure_emails
    except Exception as exc:
        logger.exception("Failed to read emails from Outlook")
        raise RuntimeError("Unable to read emails from Outlook.") from exc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    try:
        emails = get_failure_emails(50)
        if not emails:
            print("No VisualCron failure emails found.")
            raise SystemExit(0)

        for email in emails:
            print("==========================================")
            print("VISUALCRON FAILURE DETECTED")
            print("==========================================")
            print(f"Subject: {email['subject']}")
            print(f"Sender: {email['sender']}")
            print(f"Received: {email['received_time']}")
            print("==========================================")
    except Exception as exc:
        logger.error("Unable to print Outlook emails: %s", exc)
