from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.ai.ollama_client import OllamaClient
from app.ai.prompt_builder import PromptBuilder
from app.logs.log_collector import CollectedLogs
from app.outlook.parser import FailureEvent

logger = logging.getLogger(__name__)


class InvalidAIResponse(ValueError):
    """Raised when the AI response is missing or invalid."""


@dataclass(slots=True)
class AnalysisResult:
    """Structured result of the AI analysis."""

    failure_stage: str
    root_cause: str
    business_impact: str
    technical_impact: str
    recommended_resolution: str
    confidence_score: int


class LogAnalyzer:
    """Coordinate prompt building and AI analysis for failure events."""

    def __init__(self, prompt_builder: PromptBuilder | None = None, ollama_client: OllamaClient | None = None) -> None:
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.ollama_client = ollama_client or OllamaClient()

    def analyze(self, failure_event: FailureEvent, collected_logs: CollectedLogs) -> AnalysisResult:
        """Generate a prompt, send it to Ollama, and parse the response into an AnalysisResult."""
        logger.info("Generating analysis prompt")
        prompt = self.prompt_builder.build_analysis_prompt(failure_event, collected_logs)

        logger.info("AI request started")
        raw_response = self.ollama_client.generate(prompt)
        logger.info("AI response received")

        if not raw_response:
            raise InvalidAIResponse("Empty AI response")

        logger.info("Validating AI JSON response")
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            logger.exception("AI response was not valid JSON")
            raise InvalidAIResponse("AI response was not valid JSON") from exc

        if not isinstance(payload, dict):
            raise InvalidAIResponse("AI response JSON must be an object")

        failure_stage = str(payload.get("failure_stage", "")).strip()
        root_cause = str(payload.get("root_cause", "")).strip()
        confidence_score = payload.get("confidence_score", "")

        if not failure_stage or not root_cause:
            raise InvalidAIResponse("failure_stage and root_cause are required")

        try:
            confidence_value = int(confidence_score)
        except (TypeError, ValueError) as exc:
            raise InvalidAIResponse("confidence_score must be an integer") from exc

        if not 0 <= confidence_value <= 100:
            raise InvalidAIResponse("confidence_score must be between 0 and 100")

        result = AnalysisResult(
            failure_stage=failure_stage,
            root_cause=root_cause,
            business_impact=str(payload.get("business_impact", "")).strip(),
            technical_impact=str(payload.get("technical_impact", "")).strip(),
            recommended_resolution=str(payload.get("recommended_resolution", "")).strip(),
            confidence_score=confidence_value,
        )

        logger.info("Analysis completed")
        return result


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

    analyzer = LogAnalyzer()
    analysis = analyzer.analyze(sample_event, sample_logs)

    print("=====================================")
    print("AI ANALYSIS")
    print(f"Failure Stage: {analysis.failure_stage}")
    print(f"Root Cause: {analysis.root_cause}")
    print(f"Business Impact: {analysis.business_impact}")
    print(f"Technical Impact: {analysis.technical_impact}")
    print(f"Recommended Resolution: {analysis.recommended_resolution}")
    print(f"Confidence: {analysis.confidence_score}")
    print("=====================================")
