from __future__ import annotations

import logging
from typing import Any

from flask import Flask, render_template

from app.queue.queue_manager import QueueManager

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="../../templates", static_folder="../../static")

_approval_state = {
    "status": "Pending",
    "message": "Waiting for approval decision.",
    "is_finalized": False,
    "is_approved": False,
}


def reset_approval_state() -> None:
    global _approval_state
    _approval_state = {
        "status": "Pending",
        "message": "Waiting for approval decision.",
        "is_finalized": False,
        "is_approved": False,
    }


def _status_icon(status: str) -> str:
    mapping = {
        "NEW": "🟡",
        "ANALYZING": "🔵",
        "READY": "🔴",
        "APPROVED": "🟢",
        "REJECTED": "⚪",
        "SENT": "✅",
    }
    return mapping.get(status, "⚪")


def _status_label(status: str) -> str:
    return status.replace("_", " ").title()


def _fallback_queue_items() -> list[dict[str, Any]]:
    return [
        {
            "id": "sample-1",
            "job_name": "BAI2_File_Import",
            "environment": "PROD",
            "server": "BHSIEAS32",
            "received_time": "21:25",
            "status": "READY",
            "occurrence_count": 4,
            "duplicate": True,
            "selected": True,
            "analysis": {
                "failure_stage": "Execution",
                "root_cause": "The VB Script failed due to missing file permissions.",
                "business_impact": "Batch delivery was delayed and downstream reporting was affected.",
                "technical_impact": "The job stopped before final file handoff.",
                "recommended_resolution": "Fix the permissions and rerun the batch process.",
                "confidence_score": 91,
            },
            "email": {
                "subject": "RCA - BAI2_File_Import Failure - PROD",
                "body": "Dear Team,\n\nThe scheduled VisualCron job BAI2_File_Import failed in PROD. The root cause has been identified as missing file permissions.\n\nRegards,\nAI L1 Support Agent",
            },
        },
        {
            "id": "sample-2",
            "job_name": "GL_Invoice_Publish",
            "environment": "UAT",
            "server": "APPSRV02",
            "received_time": "19:42",
            "status": "NEW",
            "occurrence_count": 1,
            "duplicate": False,
            "selected": False,
            "analysis": {
                "failure_stage": "Validation",
                "root_cause": "The payload schema changed and the mapping rule rejected the file.",
                "business_impact": "Invoice publication was paused for the current cycle.",
                "technical_impact": "The downstream consumer did not receive the expected payload.",
                "recommended_resolution": "Align the schema mapping and rerun the publish job.",
                "confidence_score": 87,
            },
            "email": {
                "subject": "RCA - GL_Invoice_Publish Failure - UAT",
                "body": "Dear Team,\n\nThe publish job stopped because the file structure did not match the required mapping.\n\nRegards,\nAI L1 Support Agent",
            },
        },
    ]


def _build_queue_items() -> list[dict[str, Any]]:
    try:
        queue_manager = QueueManager()
        records = queue_manager.list_failures()
    except Exception as exc:
        logger.exception("Failed to load queue items for dashboard")
        records = []

    if not records:
        return _fallback_queue_items()

    queue_items: list[dict[str, Any]] = []
    for record in records:
        analysis = record.analysis or {
            "failure_stage": "Pending Review",
            "root_cause": "No analysis available yet.",
            "business_impact": "Awaiting review.",
            "technical_impact": "Awaiting review.",
            "recommended_resolution": "Awaiting review.",
            "confidence_score": 0,
        }
        email = record.email or {
            "subject": f"RCA - {record.job_name} Failure - {record.environment}",
            "body": "No email draft available yet.",
        }
        queue_items.append(
            {
                "id": record.id,
                "job_name": record.job_name,
                "environment": record.environment,
                "server": record.server,
                "received_time": record.received_time,
                "status": record.status,
                "occurrence_count": record.occurrence_count,
                "duplicate": record.occurrence_count > 1,
                "selected": False,
                "analysis": analysis,
                "email": email,
                "icon": _status_icon(record.status),
            }
        )

    if queue_items:
        queue_items[0]["selected"] = True
    return queue_items


def _build_view_context() -> dict[str, Any]:
    queue_items = _build_queue_items()
    selected_failure = next((item for item in queue_items if item.get("selected")), queue_items[0] if queue_items else None)

    pending_count = sum(1 for item in queue_items if item["status"] in {"NEW", "ANALYZING"})
    ready_count = sum(1 for item in queue_items if item["status"] == "READY")
    approved_count = sum(1 for item in queue_items if item["status"] == "APPROVED")
    rejected_count = sum(1 for item in queue_items if item["status"] == "REJECTED")

    workflow_steps = [
        {"label": "Failure Received", "state": "completed"},
        {"label": "Queue Registered", "state": "completed"},
        {"label": "Analysis Ready", "state": "completed" if selected_failure and selected_failure.get("analysis") else "pending"},
        {"label": "Approval Review", "state": "active"},
        {"label": "Send Pending", "state": "pending"},
    ]

    if _approval_state["is_finalized"] and _approval_state["is_approved"]:
        status_message = "Approved. Waiting to Send"
    elif _approval_state["is_finalized"]:
        status_message = "Rejected by Engineer. Email will not be sent"
    else:
        status_message = "Operations console ready for review"

    return {
        "queue_items": queue_items,
        "selected_failure": selected_failure,
        "stats": {
            "pending": pending_count,
            "ready": ready_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "queue_size": len(queue_items),
            "queue_capacity": 20,
        },
        "workflow_steps": workflow_steps,
        "approval_status": _approval_state["status"],
        "confirmation_message": _approval_state["message"] if _approval_state["is_finalized"] else "",
        "approval_finalized": _approval_state["is_finalized"],
        "status_message": status_message,
    }


@app.route("/")
def index() -> str:
    context = _build_view_context()
    return render_template("index.html", **context)


@app.post("/approve")
def approve() -> str:
    global _approval_state
    _approval_state = {
        "status": "Approved",
        "message": "Approved Successfully",
        "is_finalized": True,
        "is_approved": True,
    }
    return render_template("index.html", **_build_view_context())


@app.post("/reject")
def reject() -> str:
    global _approval_state
    _approval_state = {
        "status": "Rejected",
        "message": "Rejected Successfully",
        "is_finalized": True,
        "is_approved": False,
    }
    return render_template("index.html", **_build_view_context())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    app.run(debug=True)
