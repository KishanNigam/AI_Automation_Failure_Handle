from __future__ import annotations

import logging
from typing import Any

from flask import Flask, render_template, request

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


def _empty_failure_item() -> dict[str, Any]:
    return {
        "id": None,
        "job_name": "No Failure Events",
        "environment": "",
        "server": "",
        "received_time": "",
        "status": "NEW",
        "workflow_status": "No Failure Events",
        "occurrence_count": 0,
        "duplicate": False,
        "selected": True,
        "analysis": {
            "failure_stage": "No Failure Events",
            "root_cause": "No Failure Events",
            "business_impact": "No Failure Events",
            "technical_impact": "No Failure Events",
            "recommended_resolution": "No Failure Events",
            "confidence_score": 0,
        },
        "email": {
            "subject": "No Failure Events",
            "body": "No Failure Events",
        },
        "icon": _status_icon("NEW"),
    }


def _build_queue_items() -> list[dict[str, Any]]:
    try:
        queue_manager = QueueManager()
        records = queue_manager.list_failures()
    except Exception as exc:
        logger.exception("Failed to load queue items for dashboard")
        records = []

    logger.info("Loading %d failures into the dashboard queue", len(records))
    if not records:
        logger.info("QueueManager returned no failures; rendering empty queue state")
        return []

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
                "workflow_status": record.status,
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


def _build_view_context(selected_failure_id: str | None = None) -> dict[str, Any]:
    queue_items = _build_queue_items()
    empty_queue = not queue_items

    selected_failure = None
    if not empty_queue:
        selected_failure = next((item for item in queue_items if item.get("id") == selected_failure_id), None)
        if selected_failure is None:
            selected_failure = next((item for item in queue_items if item.get("selected")), queue_items[0])
    if selected_failure is None:
        selected_failure = _empty_failure_item()
        selected_failure_id = None

    if not empty_queue and selected_failure.get("id") is not None:
        selected_failure["approve_enabled"] = selected_failure["status"] == "READY"
        selected_failure["reject_enabled"] = selected_failure["status"] == "READY"
        selected_failure["reopen_enabled"] = selected_failure["status"] in {"APPROVED", "REJECTED"}
    else:
        selected_failure["approve_enabled"] = False
        selected_failure["reject_enabled"] = False
        selected_failure["reopen_enabled"] = False

    pending_count = sum(1 for item in queue_items if item["status"] in {"NEW", "ANALYZING"})
    ready_count = sum(1 for item in queue_items if item["status"] == "READY")
    approved_count = sum(1 for item in queue_items if item["status"] == "APPROVED")
    rejected_count = sum(1 for item in queue_items if item["status"] == "REJECTED")
    sent_count = sum(1 for item in queue_items if item["status"] == "SENT")

    workflow_steps = [
        {"label": "Failure Received", "state": "completed"},
        {"label": "Queue Registered", "state": "completed"},
        {"label": "Analysis Ready", "state": "completed" if selected_failure and selected_failure.get("analysis") else "pending"},
        {"label": "Approval Review", "state": "active"},
        {"label": "Send Pending", "state": "pending"},
    ]

    if _approval_state["is_finalized"] and _approval_state["is_approved"]:
        status_message = "Approved. Waiting to Send"
    elif _approval_state["is_finalized"] and _approval_state["status"] == "Rejected":
        status_message = "Rejected by Engineer. Email will not be sent"
    elif _approval_state["is_finalized"] and _approval_state["status"] == "Reopened":
        status_message = "Reopened. Waiting for review"
    else:
        status_message = "Operations console ready for review"

    return {
        "queue_items": queue_items,
        "selected_failure": selected_failure,
        "empty_queue": empty_queue,
        "stats": {
            "pending": pending_count,
            "ready": ready_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "sent": sent_count,
            "queue_size": len(queue_items),
            "queue_capacity": 20,
        },
        "workflow_steps": workflow_steps,
        "approval_status": _approval_state["status"],
        "confirmation_message": _approval_state["message"] if _approval_state["is_finalized"] else "",
        "approval_finalized": _approval_state["is_finalized"],
        "status_message": status_message,
        "selected_failure_id": selected_failure_id,
    }


def _get_failure_for_action(failure_id: str | None, queue_manager: QueueManager | None = None) -> Any | None:
    manager = queue_manager or QueueManager()
    if failure_id:
        return manager.get_failure(failure_id)
    return next(iter(manager.list_failures()), None)


def _apply_decision(action: str, failure_id: str | None) -> dict[str, Any]:
    global _approval_state

    queue_manager = QueueManager()
    record = _get_failure_for_action(failure_id, queue_manager=queue_manager)
    if record is None:
        logger.info("No failure selected for %s decision; rendering notification-only response", action)
        if action == "approve":
            _approval_state = {
                "status": "Approved",
                "message": "Approved Successfully",
                "is_finalized": True,
                "is_approved": True,
            }
        elif action == "reject":
            _approval_state = {
                "status": "Rejected",
                "message": "Rejected Successfully",
                "is_finalized": True,
                "is_approved": False,
            }
        elif action == "reopen":
            _approval_state = {
                "status": "Reopened",
                "message": "Reopened Successfully",
                "is_finalized": True,
                "is_approved": False,
            }
        else:
            _approval_state = {
                "status": "Pending",
                "message": "No Failure Events",
                "is_finalized": True,
                "is_approved": False,
            }
        return _build_view_context(failure_id)

    if action == "approve":
        if record.status != "READY":
            logger.warning("Rejecting invalid approve transition for %s from %s", record.id, record.status)
            _approval_state = {
                "status": "Pending",
                "message": "Invalid transition",
                "is_finalized": True,
                "is_approved": False,
            }
            return _build_view_context(record.id)
        queue_manager.approve(record.id)
        logger.info("Approved failure %s via dashboard action", record.id)
        _approval_state = {
            "status": "Approved",
            "message": "Approved Successfully",
            "is_finalized": True,
            "is_approved": True,
        }
        return _build_view_context(record.id)

    if action == "reject":
        if record.status != "READY":
            logger.warning("Rejecting invalid reject transition for %s from %s", record.id, record.status)
            _approval_state = {
                "status": "Pending",
                "message": "Invalid transition",
                "is_finalized": True,
                "is_approved": False,
            }
            return _build_view_context(record.id)
        queue_manager.reject(record.id)
        logger.info("Rejected failure %s via dashboard action", record.id)
        _approval_state = {
            "status": "Rejected",
            "message": "Rejected Successfully",
            "is_finalized": True,
            "is_approved": False,
        }
        return _build_view_context(record.id)

    if action == "reopen":
        if record.status not in {"APPROVED", "REJECTED"}:
            logger.warning("Rejecting invalid reopen transition for %s from %s", record.id, record.status)
            _approval_state = {
                "status": "Pending",
                "message": "Invalid transition",
                "is_finalized": True,
                "is_approved": False,
            }
            return _build_view_context(record.id)
        record.status = "READY"
        queue_manager.save()
        logger.info("Reopened failure %s via dashboard action", record.id)
        _approval_state = {
            "status": "Reopened",
            "message": "Reopened Successfully",
            "is_finalized": True,
            "is_approved": False,
        }
        return _build_view_context(record.id)

    logger.warning("Unsupported dashboard action requested: %s", action)
    _approval_state = {
        "status": "Pending",
        "message": "Invalid action",
        "is_finalized": True,
        "is_approved": False,
    }
    return _build_view_context(failure_id)


@app.route("/")
def index() -> str:
    context = _build_view_context(request.args.get("failure_id"))
    return render_template("index.html", **context)


@app.post("/approve")
@app.post("/approve/<failure_id>")
def approve(failure_id: str | None = None) -> str:
    return render_template("index.html", **_apply_decision("approve", failure_id))


@app.post("/reject")
@app.post("/reject/<failure_id>")
def reject(failure_id: str | None = None) -> str:
    return render_template("index.html", **_apply_decision("reject", failure_id))


@app.post("/reopen")
@app.post("/reopen/<failure_id>")
def reopen(failure_id: str | None = None) -> str:
    return render_template("index.html", **_apply_decision("reopen", failure_id))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    app.run(debug=True)
