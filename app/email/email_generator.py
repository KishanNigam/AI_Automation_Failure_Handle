from __future__ import annotations

import logging
from dataclasses import dataclass

from app.outlook.parser import FailureEvent
from app.ai.analyzer import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClientEmail:
    subject: str
    body: str


class ClientEmailGenerator:
    """Generate a client-facing email from failure analysis results."""

    def generate_email(self, failure_event: FailureEvent, analysis_result: AnalysisResult) -> ClientEmail:
        """Build the email subject and body using the analysis result."""
        logger.info("Generating client email for job %s", failure_event.job_name)

        subject = f"RCA - {failure_event.job_name} Failure - {failure_event.environment}"
        body = (
            "Dear Team,\n\n"
            f"The scheduled VisualCron job {failure_event.job_name} failed in the {failure_event.environment} environment.\n\n"
            "Root Cause\n"
            "-----------\n"
            f"{analysis_result.root_cause}\n\n"
            "Business Impact\n"
            "---------------\n"
            f"{analysis_result.business_impact}\n\n"
            "Technical Impact\n"
            "----------------\n"
            f"{analysis_result.technical_impact}\n\n"
            "Recommended Resolution\n"
            "----------------------\n"
            f"{analysis_result.recommended_resolution}\n\n"
            "Please let us know if any additional information is required.\n\n"
            "Regards,\n\n"
            "AI L1 Support Agent"
        )

        return ClientEmail(subject=subject, body=body)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    sample_event = FailureEvent(
        job_name="BAI2_File_Import",
        environment="PROD",
        server_name="BHSIEAS32",
        subject="[EXTERNAL] EAS-P5-MW - BAI2_File_Import - PROD - BHSIEAS32",
        sender="VisualCron",
        received_time="2026-07-04 00:00:00",
        body="Failure details",
    )

    sample_analysis = AnalysisResult(
        failure_stage="Execution",
        root_cause="The VB Script failed due to missing file permissions.",
        business_impact="Job data was not delivered on time.",
        technical_impact="The downstream batch process was blocked.",
        recommended_resolution="Fix permissions and rerun the job.",
        confidence_score=85,
    )

    generator = ClientEmailGenerator()
    email = generator.generate_email(sample_event, sample_analysis)

    print("=====================================")
    print("CLIENT EMAIL")
    print(f"Subject: {email.subject}")
    print("Body:")
    print(email.body)
    print("=====================================")
