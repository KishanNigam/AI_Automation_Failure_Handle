import unittest
from unittest.mock import patch

from app.ai.analyzer import AnalysisResult
from app.logs.log_collector import CollectedLogs
from app.outlook.parser import FailureEvent
from app.workflow.workflow_engine import WorkflowEngine


class FakeAnalyzer:
    def analyze(self, failure_event, collected_logs):
        return AnalysisResult(
            failure_stage="Execution",
            root_cause="Missing permissions",
            business_impact="Job delayed",
            technical_impact="Batch blocked",
            recommended_resolution="Fix permissions",
            confidence_score=88,
        )


class FakeCollector:
    def collect(self, failure_event):
        return CollectedLogs(
            visualcron_log_path=None,
            batch_log_path=None,
            vbs_log_path=None,
            visualcron_content=None,
            batch_content=None,
            vbs_content=None,
        )


class WorkflowEngineIntegrationTests(unittest.TestCase):
    def test_run_returns_structured_workflow_result(self):
        engine = WorkflowEngine(analyzer=FakeAnalyzer(), collector=FakeCollector())
        sample_email = {
            "subject": "[EXTERNAL] EAS-P5-MW - JOB1 - PROD - SERVER1",
            "sender": "VisualCron",
            "received_time": "2026-07-04 00:00:00",
            "body": "Failure details",
        }

        with patch("app.workflow.workflow_engine.get_failure_emails", return_value=[sample_email]), patch(
            "app.workflow.workflow_engine.parse_failure_email"
        ) as parse_failure_email:
            parse_failure_email.return_value = FailureEvent(
                job_name="JOB1",
                environment="PROD",
                server_name="SERVER1",
                subject=sample_email["subject"],
                sender=sample_email["sender"],
                received_time=sample_email["received_time"],
                body=sample_email["body"],
            )

            result = engine.run()

        self.assertIsNotNone(result)
        self.assertEqual(result.workflow_status, "completed")
        self.assertEqual(result.failure_event.job_name, "JOB1")
        self.assertEqual(result.analysis_result.root_cause, "Missing permissions")
        self.assertEqual(result.client_email.subject, "RCA - JOB1 Failure - PROD")


if __name__ == "__main__":
    unittest.main()
