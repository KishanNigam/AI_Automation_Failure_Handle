from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional

from app.workflow.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)


class MailMonitor:
    """Continuously monitor Outlook for new VisualCron failures."""

    def __init__(
        self,
        workflow_engine: WorkflowEngine | None = None,
        storage_path: str | None = None,
        interval_seconds: float = 30.0,
    ) -> None:
        self.workflow_engine = workflow_engine or WorkflowEngine()
        self.storage_path = Path(storage_path or "processed_mails.json")
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._processed_mail_ids: set[str] = self._load_processed_ids()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.info("Mail monitor is already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="mail-monitor", daemon=True)
        self._thread.start()
        logger.info("Mail monitor started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        logger.info("Mail monitor stopped")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run_loop(self) -> None:
        logger.info("Mail monitor loop started", extra={"event": "monitor_loop_started"})
        while not self._stop_event.is_set():
            try:
                self._process_cycle()
            except Exception as exc:  # pragma: no cover - protective guard
                logger.exception("Mail monitor loop failed: %s", exc, extra={"event": "monitor_loop_failed"})
            self._stop_event.wait(self.interval_seconds)
        logger.info("Mail monitor loop stopped", extra={"event": "monitor_loop_stopped"})

    def _process_cycle(self) -> None:
        try:
            emails = self._fetch_outlook_messages()
        except Exception as exc:
            logger.exception("Unable to read Outlook emails for monitoring: %s", exc, extra={"event": "outlook_unavailable"})
            return

        for email in emails:
            entry_id = self._extract_entry_id(email)
            if not entry_id:
                continue
            if self._is_processed(entry_id):
                continue
            self._process_email(email)
            break

    def _fetch_outlook_messages(self) -> list[dict[str, Any]]:
        try:
            import win32com.client as win32
        except ImportError as exc:
            raise RuntimeError("pywin32 is required to access Outlook via COM.") from exc

        try:
            outlook = win32.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            inbox = namespace.GetDefaultFolder(6)
            items = inbox.Items
            items.Sort("[ReceivedTime]", True)

            failure_emails: list[dict[str, Any]] = []
            for item in items:
                if len(failure_emails) >= 50:
                    break
                try:
                    if getattr(item, "Class", None) != 43:
                        continue

                    subject = getattr(item, "Subject", "") or ""
                    if not subject.startswith("[EXTERNAL] EAS-P5-MW"):
                        continue

                    failure_emails.append(
                        {
                            "entry_id": getattr(item, "EntryID", None),
                            "subject": subject,
                            "sender": getattr(item, "SenderName", None) or getattr(item, "SenderEmailAddress", None),
                            "received_time": getattr(item, "ReceivedTime", None),
                            "body": getattr(item, "Body", None),
                        }
                    )
                except Exception as exc:
                    logger.exception("Failed to read an Outlook email entry", extra={"event": "outlook_item_error"})
                    raise RuntimeError("Unable to read one or more Outlook emails.") from exc

            return failure_emails
        except Exception as exc:
            logger.exception("Failed to read emails from Outlook", extra={"event": "outlook_read_error"})
            raise RuntimeError("Unable to read emails from Outlook.") from exc

    def _process_email(self, email: dict[str, Any]) -> None:
        entry_id = self._extract_entry_id(email)
        if not entry_id:
            logger.warning("Skipping email without unique identifier: %s", email)
            return

        if self._is_processed(entry_id):
            logger.info("Skipping already processed email %s", entry_id)
            return

        logger.info("Processing new Outlook email %s", entry_id, extra={"event": "mail_processing_started", "entry_id": entry_id})
        try:
            workflow_result = self.workflow_engine.run()
            if getattr(workflow_result, "workflow_status", None) in {"completed", "no_failure"}:
                self._mark_processed(entry_id)
                logger.info("Recorded processed email %s", entry_id, extra={"event": "mail_processed", "entry_id": entry_id})
            else:
                logger.warning("Workflow did not complete for email %s", entry_id, extra={"event": "workflow_incomplete", "entry_id": entry_id})
        except Exception as exc:
            logger.exception("Failed to process Outlook email %s: %s", entry_id, exc, extra={"event": "mail_processing_failed", "entry_id": entry_id})

    def _extract_entry_id(self, email: dict[str, Any]) -> str | None:
        value = email.get("entry_id")
        if value:
            return str(value)
        return None

    def _is_processed(self, entry_id: str) -> bool:
        with self._lock:
            return entry_id in self._processed_mail_ids

    def _mark_processed(self, entry_id: str) -> None:
        with self._lock:
            self._processed_mail_ids.add(entry_id)
            self._persist_processed_ids()

    def _persist_processed_ids(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self.storage_path.open("w", encoding="utf-8") as handle:
            json.dump(sorted(self._processed_mail_ids), handle, indent=2)

    def _load_processed_ids(self) -> set[str]:
        if not self.storage_path.exists():
            return set()
        try:
            with self.storage_path.open("r", encoding="utf-8") as handle:
                content = json.load(handle)
            if isinstance(content, list):
                return {str(item) for item in content}
        except Exception as exc:
            logger.exception("Failed to load processed mail IDs from %s: %s", self.storage_path, exc)
        return set()

    def _processed_ids(self) -> set[str]:
        with self._lock:
            return set(self._processed_mail_ids)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    monitor = MailMonitor()
    logger.info("Mail Monitor Started")
    monitor.start()
    try:
        while True:
            logger.info("Checking Outlook...")
            time.sleep(30)
            logger.info("Sleeping 30 seconds...")
    except KeyboardInterrupt:
        logger.info("Shutting down mail monitor")
        monitor.stop()
