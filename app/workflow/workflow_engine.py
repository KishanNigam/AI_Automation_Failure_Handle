from __future__ import annotations

import logging
from dataclasses import dataclass

from app.ai.analyzer import AnalysisResult, LogAnalyzer
from app.email.email_generator import ClientEmail, ClientEmailGenerator
from app.logs.log_collector import LogCollector
from app.outlook.parser import FailureEvent, parse_failure_email
from app.outlook.reader import get_failure_emails
from app.queue.models import FailureRecord
from app.queue.queue_manager import QueueManager

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkflowResult:
    """Structured outcome returned by the workflow engine."""

    failure_event: FailureEvent | None
    analysis_result: AnalysisResult | None
    client_email: ClientEmail | None
    workflow_status: str
    error_message: str | None = None


class WorkflowEngine:
    """Orchestrate the VisualCron AI support workflow."""

    def __init__(
        self,
        analyzer: LogAnalyzer | None = None,
        collector: LogCollector | None = None,
        email_generator: ClientEmailGenerator | None = None,
        queue_manager: QueueManager | None = None,
    ) -> None:
        self.analyzer = analyzer or LogAnalyzer()
        self.collector = collector or LogCollector()
        self.email_generator = email_generator or ClientEmailGenerator()
        self.queue_manager = queue_manager or QueueManager()

    def run(self) -> WorkflowResult:
        """Execute the workflow and return a structured workflow result."""
        try:
            logger.info("Workflow started: reading latest VisualCron failure email")
            emails = get_failure_emails(limit=1)
            if not emails:
                logger.warning("No failure email found by the Outlook Reader")
                return WorkflowResult(
                    failure_event=None,
                    analysis_result=None,
                    client_email=None,
                    workflow_status="no_failure",
                    error_message="No failure email found",
                )

            logger.info("Workflow step completed: retrieved latest failure email")
            raw_email = emails[0]

            logger.info("Workflow started: parsing failure email")
            failure_event = parse_failure_email(raw_email)
            logger.info("Workflow step completed: parsed failure email")

            logger.info("Workflow started: collecting related logs")
            collected_logs = self.collector.collect(failure_event)
            logger.info("Workflow step completed: collected logs")

            logger.info("Workflow started: analyzing failure event")
            analysis_result = self.analyzer.analyze(failure_event, collected_logs)
            logger.info("Workflow step completed: analysis completed")

            client_email = self.email_generator.generate_email(failure_event, analysis_result)
            self._persist_failure_record(
                failure_event=failure_event,
                analysis_result=analysis_result,
                client_email=client_email,
            )
            self._print_report(failure_event, analysis_result)
            logger.info("Workflow completed successfully")
            return WorkflowResult(
                failure_event=failure_event,
                analysis_result=analysis_result,
                client_email=client_email,
                workflow_status="completed",
            )
        except Exception as exc:
            stage = self._identify_stage(exc)
            logger.exception("Workflow failed at stage: %s", stage)
            return WorkflowResult(
                failure_event=None,
                analysis_result=None,
                client_email=None,
                workflow_status="failed",
                error_message=f"{stage}: {exc}",
            )

    def _persist_failure_record(
        self,
        *,
        failure_event: FailureEvent,
        analysis_result: AnalysisResult,
        client_email: ClientEmail,
    ) -> None:
        analysis_payload = {
            "failure_stage": analysis_result.failure_stage,
            "root_cause": analysis_result.root_cause,
            "business_impact": analysis_result.business_impact,
            "technical_impact": analysis_result.technical_impact,
            "recommended_resolution": analysis_result.recommended_resolution,
            "confidence_score": analysis_result.confidence_score,
        }
        email_payload = {
            "subject": client_email.subject,
            "body": client_email.body,
        }
        self.queue_manager.add_failure(
            job_name=failure_event.job_name,
            environment=failure_event.environment,
            server=failure_event.server_name,
            subject=failure_event.subject,
            received_time=failure_event.received_time,
            root_cause=analysis_result.root_cause,
            analysis=analysis_payload,
            email=email_payload,
        )
        record = self.queue_manager.get_by_fingerprint(
            FailureRecord.create(
                job_name=failure_event.job_name,
                environment=failure_event.environment,
                server=failure_event.server_name,
                subject=failure_event.subject,
                received_time=failure_event.received_time,
                root_cause=analysis_result.root_cause,
            ).fingerprint
        )
        if record is not None:
            record.status = "READY"
            self.queue_manager.save()
        logger.info("Stored completed failure record for %s in queue manager", failure_event.job_name)

    @staticmethod
    def _identify_stage(exc: Exception) -> str:
        message = str(exc).lower()
        if "outlook" in message or "email" in message:
            return "Outlook Reader"
        if "parse" in message or "failure email format" in message:
            return "Failure Email Parser"
        if "collect" in message or "log" in message:
            return "Log Collector"
        if "ai" in message or "ollama" in message or "response" in message:
            return "AI Analyzer"
        return "Workflow"

    @staticmethod
    def _print_report(failure_event: FailureEvent, analysis_result: AnalysisResult) -> None:
        print("========================================")
        print("VISUALCRON AI RCA REPORT")
        print(f"Job Name: {failure_event.job_name}")
        print(f"Environment: {failure_event.environment}")
        print(f"Server: {failure_event.server_name}")
        print(f"Failure Stage: {analysis_result.failure_stage}")
        print(f"Root Cause: {analysis_result.root_cause}")
        print(f"Business Impact: {analysis_result.business_impact}")
        print(f"Technical Impact: {analysis_result.technical_impact}")
        print(f"Recommended Resolution: {analysis_result.recommended_resolution}")
        print(f"Confidence Score: {analysis_result.confidence_score}")
        print("========================================")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    engine = WorkflowEngine()
    engine.run()
