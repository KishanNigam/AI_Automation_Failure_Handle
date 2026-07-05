import os
import tempfile
import unittest

from app.queue.queue_manager import QueueManager
from app.ui import dashboard as dashboard_module
from app.ui.dashboard import app, reset_approval_state


class DashboardApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(self.temp_dir.name, "queue.json")
        self.original_queue_manager = dashboard_module.QueueManager
        dashboard_module.QueueManager = lambda *args, **kwargs: QueueManager(storage_path=self.storage_path, max_size=20)
        self.client = app.test_client()
        reset_approval_state()

    def tearDown(self):
        dashboard_module.QueueManager = self.original_queue_manager
        self.temp_dir.cleanup()

    def test_approve_route_updates_state_and_message(self):
        response = self.client.post("/approve")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Approved Successfully", response.get_data(as_text=True))
        self.assertIn("Approved", response.get_data(as_text=True))
        self.assertIn("Waiting to Send", response.get_data(as_text=True))

    def test_reject_route_updates_state_and_message(self):
        response = self.client.post("/reject")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Rejected Successfully", response.get_data(as_text=True))
        self.assertIn("Rejected by Engineer", response.get_data(as_text=True))
        self.assertIn("Email will not be sent", response.get_data(as_text=True))

    def test_engineer_routes_update_queue_status(self):
        queue_manager = QueueManager(storage_path=self.storage_path, max_size=20)
        record = queue_manager.add_failure(
            job_name="JOB1",
            environment="PROD",
            server="SERVER1",
            subject="subject",
            received_time="2026-07-05",
            root_cause="missing permission",
        )
        record.status = "READY"
        queue_manager.save()

        approve_response = self.client.post(f"/approve/{record.id}")
        self.assertEqual(approve_response.status_code, 200)
        reloaded = QueueManager(storage_path=self.storage_path, max_size=20).get_failure(record.id)
        self.assertEqual(reloaded.status, "APPROVED")

        reject_response = self.client.post(f"/reject/{record.id}")
        self.assertEqual(reject_response.status_code, 200)
        reloaded = QueueManager(storage_path=self.storage_path, max_size=20).get_failure(record.id)
        self.assertEqual(reloaded.status, "APPROVED")

        reopen_response = self.client.post(f"/reopen/{record.id}")
        self.assertEqual(reopen_response.status_code, 200)
        reloaded = QueueManager(storage_path=self.storage_path, max_size=20).get_failure(record.id)
        self.assertEqual(reloaded.status, "READY")


if __name__ == "__main__":
    unittest.main()
