from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.outlook.parser import FailureEvent

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CollectedLogs:
    """Container for the latest collected log contents for a failure event."""

    visualcron_log_path: str | None
    batch_log_path: str | None
    vbs_log_path: str | None
    visualcron_content: str | None
    batch_content: str | None
    vbs_content: str | None


class LogCollector:
    """Collect the latest log files for a given failure event."""

    def __init__(self, base_root: str | None = None) -> None:
        self.base_root = Path(base_root or r"C:\Users\nigam\Downloads\Kishan\LogSystem")

    def _latest_file(self, directory: Path, *, include_batch: bool | None = None, include_vbs: bool | None = None) -> Path | None:
        """Return the latest matching file in a directory based on modification time."""
        if not directory.exists() or not directory.is_dir():
            return None

        files = [path for path in directory.iterdir() if path.is_file()]
        if not files:
            return None

        filtered_files = files
        if include_batch is True:
            filtered_files = [path for path in files if "_batch_" in path.name.lower()]
        elif include_batch is False:
            filtered_files = [path for path in files if "_batch_" not in path.name.lower() and "_vbs_" not in path.name.lower()]

        if include_vbs is True:
            filtered_files = [path for path in files if "_vbs_" in path.name.lower()]
        elif include_vbs is False:
            filtered_files = [path for path in files if "_vbs_" not in path.name.lower() and "_batch_" not in path.name.lower()]

        if not filtered_files:
            return None

        return max(filtered_files, key=lambda path: path.stat().st_mtime, default=None)

    def _read_file_content(self, path: Path | None) -> str | None:
        """Read a file and return its contents or None when unavailable."""
        if path is None or not path.exists() or not path.is_file():
            return None

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return content if content.strip() else None
        except Exception as exc:
            logger.exception("Failed to read log file: %s", path)
            return None

    def collect(self, event: FailureEvent) -> CollectedLogs:
        """Collect the latest logs associated with a failure event."""
        try:
            server_name = event.server_name
            job_name = event.job_name

            visualcron_dir = self.base_root / server_name / "visualcron" / "logs" / job_name
            batch_dir = self.base_root / server_name / "Server" / "Custom" / "log" / job_name
            vbs_dir = self.base_root / server_name / "Server" / "Custom" / "log" / job_name

            visualcron_file = self._latest_file(visualcron_dir, include_batch=False, include_vbs=False)
            batch_file = self._latest_file(batch_dir, include_batch=True)
            vbs_file = self._latest_file(vbs_dir, include_vbs=True)

            return CollectedLogs(
                visualcron_log_path=str(visualcron_file) if visualcron_file else None,
                batch_log_path=str(batch_file) if batch_file else None,
                vbs_log_path=str(vbs_file) if vbs_file else None,
                visualcron_content=self._read_file_content(visualcron_file),
                batch_content=self._read_file_content(batch_file),
                vbs_content=self._read_file_content(vbs_file),
            )
        except Exception as exc:
            logger.exception("Failed to collect logs for failure event")
            raise RuntimeError("Unable to collect logs") from exc


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

    collector = LogCollector()
    collected = collector.collect(sample_event)

    print("===================================")
    print("Latest VisualCron Log")
    print(collected.visualcron_log_path or "No log found")
    print("Latest Batch Log")
    print(collected.batch_log_path or "No log found")
    print("Latest VBS Log")
    print(collected.vbs_log_path or "No log found")
    print("===================================")
