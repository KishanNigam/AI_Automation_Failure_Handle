import os
import tempfile
import time
import unittest

from app.monitor.mail_monitor import MailMonitor


class FakeWorkflowEngine:
    def __init__(self) -> None:
        self.calls = 0

    def run(self):
        self.calls += 1
        return type("WorkflowResult", (), {"workflow_status": "completed"})()


class MailMonitorTests(unittest.TestCase):
    def test_monitor_processes_new_mail_once_and_skips_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = os.path.join(temp_dir, "processed_mails.json")
            workflow_engine = FakeWorkflowEngine()
            monitor = MailMonitor(
                workflow_engine=workflow_engine,
                storage_path=storage_path,
                interval_seconds=0.01,
            )

            emails = [
                {
                    "entry_id": "mail-1",
                    "subject": "[EXTERNAL] EAS-P5-MW - JOB1 - PROD - SERVER1",
                    "sender": "VisualCron",
                    "received_time": "2026-07-05",
                    "body": "Failure details",
                },
                {
                    "entry_id": "mail-2",
                    "subject": "[EXTERNAL] EAS-P5-MW - JOB2 - PROD - SERVER2",
                    "sender": "VisualCron",
                    "received_time": "2026-07-05",
                    "body": "Failure details",
                },
            ]

            monitor._fetch_outlook_messages = lambda: list(emails)

            monitor.start()
            time.sleep(0.2)
            self.assertTrue(monitor.is_running())
            monitor.stop()

            self.assertFalse(monitor.is_running())
            self.assertEqual(workflow_engine.calls, 2)
            self.assertTrue(os.path.exists(storage_path))
            self.assertEqual(monitor._processed_ids(), {"mail-1", "mail-2"})


if __name__ == "__main__":
    unittest.main()
