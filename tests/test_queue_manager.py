import os
import tempfile
import unittest
from datetime import datetime, timezone

from app.queue.models import FailureRecord
from app.queue.queue_manager import QueueManager


class QueueManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = os.path.join(self.temp_dir.name, "queue.json")
        self.manager = QueueManager(storage_path=self.storage_path, max_size=3)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_failure_creates_new_record_for_new_fingerprint(self):
        record = self.manager.add_failure(
            job_name="JOB1",
            environment="PROD",
            server="SERVER1",
            subject="subject",
            received_time="2026-07-05",
            root_cause="missing permission",
        )

        self.assertEqual(record.status, "NEW")
        self.assertEqual(record.occurrence_count, 1)
        self.assertEqual(len(self.manager.list_failures()), 1)

    def test_add_failure_increments_occurrence_for_existing_fingerprint(self):
        self.manager.add_failure(job_name="JOB1", environment="PROD", server="SERVER1", subject="subject", received_time="2026-07-05", root_cause="missing permission")
        duplicate = self.manager.add_failure(job_name="JOB1", environment="PROD", server="SERVER1", subject="subject", received_time="2026-07-05", root_cause="missing permission")

        self.assertEqual(duplicate.occurrence_count, 2)
        self.assertEqual(len(self.manager.list_failures()), 1)

    def test_queue_removes_oldest_when_exceeding_max_size(self):
        first = self.manager.add_failure(job_name="JOB1", environment="PROD", server="SERVER1", subject="s1", received_time="t1", root_cause="r1")
        second = self.manager.add_failure(job_name="JOB2", environment="PROD", server="SERVER2", subject="s2", received_time="t2", root_cause="r2")
        third = self.manager.add_failure(job_name="JOB3", environment="PROD", server="SERVER3", subject="s3", received_time="t3", root_cause="r3")
        fourth = self.manager.add_failure(job_name="JOB4", environment="PROD", server="SERVER4", subject="s4", received_time="t4", root_cause="r4")

        self.assertEqual(len(self.manager.list_failures()), 3)
        self.assertIsNone(self.manager.get_failure(first.id))
        self.assertEqual(self.manager.get_failure(second.id).job_name, "JOB2")
        self.assertEqual(self.manager.get_failure(third.id).job_name, "JOB3")
        self.assertEqual(self.manager.get_failure(fourth.id).job_name, "JOB4")

    def test_mark_status_and_persist(self):
        record = self.manager.add_failure(job_name="JOB1", environment="PROD", server="SERVER1", subject="s", received_time="t", root_cause="r")
        self.manager.approve(record.id)
        reloaded = QueueManager(storage_path=self.storage_path, max_size=3)
        self.assertEqual(reloaded.get_failure(record.id).status, "APPROVED")

    def test_datetime_received_time_persists_and_round_trips(self):
        received_time = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
        record = self.manager.add_failure(
            job_name="JOB1",
            environment="PROD",
            server="SERVER1",
            subject="subject",
            received_time=received_time,
            root_cause="missing permission",
        )

        self.assertEqual(record.received_time, received_time)

        reloaded = QueueManager(storage_path=self.storage_path, max_size=3)
        reloaded_record = reloaded.get_failure(record.id)
        self.assertIsNotNone(reloaded_record)
        self.assertIsInstance(reloaded_record.received_time, datetime)
        self.assertEqual(reloaded_record.received_time, received_time)


if __name__ == "__main__":
    unittest.main()
