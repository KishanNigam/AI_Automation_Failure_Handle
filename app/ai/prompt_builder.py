from __future__ import annotations

import logging
from typing import Any

from app.logs.log_collector import CollectedLogs
from app.outlook.parser import FailureEvent

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Build structured prompts for analyzing VisualCron failure events."""

    def build_analysis_prompt(self, failure_event: FailureEvent, collected_logs: CollectedLogs) -> str:
        """Construct a prompt containing the failure details and collected logs."""
        try:
            prompt_parts: list[str] = [
                "--------------------------------------------------",
                "ROLE",
                "",
                "You are a Senior L1 Production Support Engineer responsible for analyzing VisualCron job failures.",
                "--------------------------------------------------",
                "",
                "TASK",
                "",
                "Analyze the provided failure information and execution logs.",
                "Determine:",
                "",
                "- Failure Stage",
                "- Root Cause",
                "- Business Impact",
                "- Technical Impact",
                "- Recommended Resolution",
                "- Confidence Score",
                "--------------------------------------------------",
                "",
                "FAILURE EMAIL",
                "",
                f"Job Name: {failure_event.job_name}",
                f"Environment: {failure_event.environment}",
                f"Server: {failure_event.server_name}",
                f"Failure Time: {failure_event.received_time}",
                f"Subject: {failure_event.subject}",
                "--------------------------------------------------",
                "",
                "VISUALCRON LOG",
                "",
                collected_logs.visualcron_content or "No VisualCron log content provided.",
                "--------------------------------------------------",
                "",
                "BATCH LOG",
                "",
                collected_logs.batch_content or "No Batch log content provided.",
                "--------------------------------------------------",
                "",
                "VB SCRIPT LOG",
                "",
                collected_logs.vbs_content or "No VB Script log content provided.",
                "--------------------------------------------------",
                "",
                "STRICT OUTPUT FORMAT",
                "",
                "The AI MUST return ONLY valid JSON.",
                "",
                "Required JSON format:",
                "{",
                '    "failure_stage": "",',
                '    "root_cause": "",',
                '    "business_impact": "",',
                '    "technical_impact": "",',
                '    "recommended_resolution": "",',
                '    "confidence_score": ""',
                "}",
                "--------------------------------------------------",
                "",
                "ANALYSIS PRIORITY",
                "",
                "Analyze logs in this order:",
                "1. VB Script Log",
                "2. Batch Log",
                "3. VisualCron Log",
                "4. Failure Email",
                "--------------------------------------------------",
                "",
                "ROOT CAUSE RULE",
                "",
                "You MUST identify the FIRST explicit ERROR line.",
                "Use that error as the root cause.",
                "If an ERROR section exists, you MUST prioritize it over assumptions.",
                "Quote the evidence internally before generating the RCA.",
                "Ignore downstream or cascading failures.",
                "Do not report secondary failures as the root cause.",
                "Never invent script errors unless the logs explicitly mention them.",
                "--------------------------------------------------",
                "",
                "CONFIDENCE SCORE",
                "",
                "Return confidence_score as an integer between 0 and 100.",
                "--------------------------------------------------",
                "",
                "RULES",
                "",
                "- Do not explain your reasoning.",
                "- Do not return markdown.",
                "- Do not return code blocks.",
                "- Do not return extra text.",
                "- Return ONLY valid JSON.",
                "- Base the answer ONLY on the supplied logs.",
                "- If evidence is insufficient, clearly mention that in the corresponding field.",
                "- Do not invent missing information.",
                "- Never use words like Possible, Likely, Maybe, or Could be unless the logs contain insufficient evidence.",
                "--------------------------------------------------",
            ]
            return "\n".join(prompt_parts)
        except Exception as exc:
            logger.exception("Failed to build analysis prompt")
            raise RuntimeError("Unable to build analysis prompt") from exc


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

    sample_logs = CollectedLogs(
        visualcron_log_path="C:/temp/visualcron.log",
        batch_log_path="C:/temp/batch.log",
        vbs_log_path="C:/temp/vbs.log",
        visualcron_content="VisualCron job started and failed during execution.",
        batch_content="Batch job reported an error.",
        vbs_content="VB Script failed at startup.",
    )

    builder = PromptBuilder()
    prompt = builder.build_analysis_prompt(sample_event, sample_logs)
    print(prompt)
