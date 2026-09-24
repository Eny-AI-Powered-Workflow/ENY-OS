# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/enrollment.py
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging
from uuid import UUID

from app.models.batch_execution_result import BatchExecutionResult
from app.models.batch_retry import BatchRetry
from app.models.cohort_approval import CohortApproval
from app.models.enrollment_audit import EnrollmentAudit
from app.models.enrollment_audit import EnrollmentAudit
from app.services.batch_execution_service import retry_batch_result
from app.services.ghl_service import ghl_service
from app.services.n8n_service import N8NService

router = APIRouter()
logger = logging.getLogger(__name__)
QUEUE_STATES = {"new", "assigned", "contacted", "qualified", "closed"}
QUEUE_TRANSITIONS = {
    "new": {"assigned"},
    "assigned": {"contacted"},
    "contacted": {"qualified", "closed"},
    "qualified": {"closed"},
    "closed": set(),
}
SLA_RULES = {
    "new_owner_minutes": 15,
    "assigned_contact_minutes": 60,
    "contacted_follow_up_hours": 24,
    "workflow_retry_minutes": 30,
    "data_quality_hours": 24,
}
OPERATING_POLICY = {
    "ownership": [
        "Every hot lead is claimed before outreach.",
        "The assigned owner remains accountable until closed, enrolled, or escalated.",
        "Unassigned hot leads are reviewed within 15 minutes.",
    ],
    "follow_up": [
        "Run the approved follow-up workflow only from an assigned lead.",
        "Record response, next step, booking, and outcome in the lifecycle.",
        "Do not skip lifecycle stages without an auditable reason.",
    ],
    "escalation": [
        "Escalate stale work, failed write-back, and exhausted retries.",
        "A recovery decision is required before rerun.",
    ],
    "weekly_review": [
        "Review intake, no-contact aging, source conversion, owner workload, and closed outcomes.",
        "Assign an owner and due date to every open alert.",
    ],
}
LIFECYCLE_STAGES = {
    "not_started",
    "queued",
    "outreach_sent",
    "responded",
    "next_step",
    "booked",
    "enrolled",
    "lost",
    "failed",
}
LIFECYCLE_TRANSITIONS = {
    "not_started": {"queued", "failed"},
    "queued": {"outreach_sent", "responded", "failed"},
    "outreach_sent": {"responded", "failed"},
    "responded": {"next_step", "booked", "lost"},
    "next_step": {"booked", "lost"},
    "booked": {"enrolled", "lost"},
    "enrolled": set(),
    "lost": set(),
    "failed": {"queued", "lost"},
}


class QueueStateRequest(BaseModel):
    state: str = Field(..., min_length=1, max_length=30)
    reason: str = Field(..., min_length=3, max_length=500)


class BatchDecisionRequest(BaseModel):
    decision: Literal["rerun", "hold", "escalate"]
    reason: str = Field(..., min_length=3, max_length=500)
    failure_class: Optional[Literal[
        "crm_contact_missing",
        "crm_write",
        "workflow",
        "rate_limit",
        "data_quality",
        "unknown",
    ]] = None


class FollowUpLifecycleRequest(BaseModel):
    stage: Literal[
        "queued",
        "outreach_sent",
        "responded",
        "next_step",
        "booked",
        "enrolled",
        "lost",
        "failed",
    ]
    reason: str = Field(..., min_length=3, max_length=500)
    next_step: Optional[str] = Field(None, max_length=500)
    enrollment_outcome: Optional[str] = Field(None, max_length=200)


def _audit(db: Session, current_user: Any, result_id: Any, event_type: str, details: dict[str, Any]) -> None:
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=result_id,
        event_type=event_type,
        details=details,
    ))
    db.commit()


def _normalize_int(value: Any, default: int) -> int:
    if hasattr(value, "default"):
        value = getattr(value, "default")
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _serialize_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _hours_since(value: Any) -> float:
    if value is None:
        return float("inf")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return float("inf")
        value = parsed
    if not hasattr(value, "tzinfo") or value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - value.astimezone(timezone.utc)).total_seconds() / 3600.0


def _transition_queue_state(
    result: BatchExecutionResult,
    target_state: str,
    actor_id: Any,
    reason: str,
) -> str:
    previous_state = getattr(result, "queue_status", "new")
    if target_state not in QUEUE_STATES:
        raise HTTPException(status_code=422, detail=f"Invalid queue state: {target_state}")
    if target_state not in QUEUE_TRANSITIONS.get(previous_state, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid queue transition: {previous_state} -> {target_state}",
        )
    result.queue_status = target_state
    result.last_action_at = datetime.now(timezone.utc)
    return previous_state

@router.get("/metrics", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get enrollment dashboard metrics.
    Requires leads:read permission.
    """
    try:
        contacts, inventory = await ghl_service.get_all_contacts()
        pipeline = await ghl_service.get_pipeline_data()
        hot_count = db.query(func.count(BatchExecutionResult.id)).filter(
            BatchExecutionResult.category == "hot",
            BatchExecutionResult.queue_status != "closed",
        ).scalar() or 0
        pending_retries = db.query(func.count(BatchExecutionResult.id)).filter(
            BatchExecutionResult.status == "failed",
        ).scalar() or 0
        metrics = {
            "totalLeads": len(contacts),
            "newLeadsToday": len([
                contact for contact in contacts
                if str(contact.get("dateAdded", ""))[:10] == datetime.now(timezone.utc).date().isoformat()
            ]),
            "conversionRate": round(float(pipeline.get("conversion_rate", 0)) * 100, 2),
            "revenuePipeline": pipeline.get("revenue_forecast", 0),
            "hotLeads": hot_count,
            "retryPending": pending_retries,
            "crmStatus": inventory.get("status", "unknown"),
        }
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching enrollment metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )

@router.get("/leads", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_leads(
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get enrollment leads.
    Requires leads:read permission.
    """
    try:
        leads = await ghl_service.get_enrollment_leads(limit=limit, search=search or "")
        return {"leads": leads, "total": len(leads), "limit": limit, "search": search or ""}
    except Exception as e:
        logger.error(f"Error fetching enrollment leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch leads: {str(e)}"
        )


@router.get("/hot-leads", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_hot_leads(
    limit: int = Query(20, ge=1, le=100),
    min_score: int = Query(80, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the current hot-lead queue sourced from approved execution results."""
    try:
        limit = _normalize_int(limit, 20)
        min_score = _normalize_int(min_score, 80)
        current_user_id = str(current_user.id)

        rows = (
            db.query(BatchExecutionResult)
            .filter(BatchExecutionResult.category == "hot")
            .filter(BatchExecutionResult.score >= min_score)
            .filter(
                (BatchExecutionResult.status.in_(["scored", "queued", "hot"]))
                | (BatchExecutionResult.assigned_user_id == current_user_id)
            )
            .order_by(BatchExecutionResult.created_at.desc())
            .limit(limit)
            .all()
        )

        leads = [
            {
                "id": str(row.contact_id),
                "result_id": str(row.id),
                "contact_id": row.contact_id,
                "firstName": (row.contact_name or "").split(" ")[0] if row.contact_name else "",
                "lastName": " ".join((row.contact_name or "").split(" ")[1:]) if row.contact_name else "",
                "email": row.email,
                "phone": row.phone,
                "score": row.score,
                "source": getattr(row, "source", None),
                "tags": row.tags or [row.category or "hot"],
                "category": row.category,
                "approval_id": str(row.approval_id) if row.approval_id else None,
                "status": getattr(row, "queue_status", "new"),
                "lifecycle_stage": getattr(row, "lifecycle_stage", "not_started"),
                "next_step": getattr(row, "next_step", None),
                "assigned_user_id": str(row.assigned_user_id) if row.assigned_user_id else None,
                "assigned_to_current_user": (
                    str(row.assigned_user_id) == current_user_id
                    if row.assigned_user_id
                    else False
                ),
                "execution_status": row.status,
                "created_at": _serialize_datetime(getattr(row, "created_at", None)),
            }
            for row in rows
        ]
        return {"leads": leads, "total": len(leads), "limit": limit, "min_score": min_score}
    except Exception as e:
        logger.error(f"Error fetching hot leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch hot leads: {str(e)}",
        )


@router.get("/batch-results", dependencies=[Depends(require_permission("leads:read"))])
async def get_batch_execution_results(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the approved batch execution ledger for review and retry tracking."""
    try:
        limit = _normalize_int(limit, 20)

        rows = (
            db.query(BatchExecutionResult)
            .order_by(BatchExecutionResult.created_at.desc())
            .limit(limit)
            .all()
        )

        summary_rows = db.query(BatchExecutionResult).all()
        summary = {
            "total": len(summary_rows),
            "succeeded": len([row for row in summary_rows if row.status in {"scored", "already_scored"}]),
            "pending": len([row for row in summary_rows if row.status in {"pending", "queued"}]),
            "failed": len([row for row in summary_rows if row.status == "failed"]),
            "exhausted": len([row for row in summary_rows if row.status == "exhausted"]),
            "held": len([row for row in summary_rows if row.status == "held"]),
            "escalated": len([row for row in summary_rows if row.status == "escalated"]),
            "rerun_approved": len([row for row in summary_rows if getattr(row, "operating_decision", "hold") == "rerun"]),
        }

        results = [
            {
                "id": str(row.id),
                "approval_id": str(row.approval_id) if row.approval_id else None,
                "cohort_name": row.cohort_name,
                "contact_id": row.contact_id,
                "contact_name": getattr(row, "contact_name", None),
                "email": getattr(row, "email", None),
                "phone": getattr(row, "phone", None),
                "source": getattr(row, "source", None),
                "score": row.score,
                "category": row.category,
                "status": row.status,
                "error": row.error,
                "retry_count": row.retry_count,
                "operating_decision": getattr(row, "operating_decision", "hold"),
                "failure_class": getattr(row, "failure_class", None),
                "recovery_owner_id": str(row.recovery_owner_id) if getattr(row, "recovery_owner_id", None) else None,
                "recovery_status": getattr(row, "recovery_status", "unassigned"),
                "created_at": _serialize_datetime(getattr(row, "created_at", None)),
            }
            for row in rows
        ]
        return {"results": results, "total": len(results), "limit": limit, "summary": summary}
    except Exception as e:
        logger.error(f"Error fetching batch execution results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch batch execution results: {str(e)}",
        )


@router.get("/operations", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_operations(
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    mine: bool = Query(False),
    unassigned: bool = Query(False),
    source: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Return the shared Enrollment follow-up queue and its recent audit trail."""
    query = db.query(BatchExecutionResult)
    if status_filter:
        query = query.filter(BatchExecutionResult.queue_status == status_filter)
    if mine:
        query = query.filter(BatchExecutionResult.assigned_user_id == current_user.id)
    if unassigned:
        query = query.filter(BatchExecutionResult.assigned_user_id.is_(None))
    if source:
        query = query.filter(BatchExecutionResult.source == source)
    if min_score is not None:
        query = query.filter(BatchExecutionResult.score >= min_score)
    if max_score is not None:
        query = query.filter(BatchExecutionResult.score <= max_score)
    results = query.order_by(BatchExecutionResult.created_at.desc()).limit(limit).all()
    monitoring_rows = db.query(BatchExecutionResult).all()
    audits = db.query(EnrollmentAudit).order_by(
        EnrollmentAudit.created_at.desc()
    ).limit(limit).all()

    try:
        contacts, inventory = await ghl_service.get_all_contacts()
        crm_status = inventory.get("status", "connected") if isinstance(inventory, dict) else "connected"
    except Exception:
        contacts = []
        crm_status = "degraded"

    summary = {
        "total": len(results),
        "new": len([row for row in results if getattr(row, "queue_status", "new") == "new"]),
        "assigned": len([row for row in results if getattr(row, "queue_status", "new") == "assigned"]),
        "contacted": len([row for row in results if getattr(row, "queue_status", "new") == "contacted"]),
        "qualified": len([row for row in results if getattr(row, "queue_status", "new") == "qualified"]),
        "closed": len([row for row in results if getattr(row, "queue_status", "new") == "closed"]),
        "follow_up_failed": len([row for row in results if getattr(row, "follow_up_status", "not_started") == "failed"]),
        "new_hot": len([row for row in results if getattr(row, "queue_status", "new") == "new" and row.category == "hot"]),
        "my_assigned": len([row for row in results if str(getattr(row, "assigned_user_id", "")) == str(current_user.id)]),
        "uncontacted_assigned": len([row for row in results if getattr(row, "queue_status", "new") == "assigned"]),
        "ownerless_leads": len([
            row for row in results
            if row.category == "hot" and getattr(row, "assigned_user_id", None) is None
        ]),
        "stale_leads": len([
            row for row in results
            if getattr(row, "queue_status", "new") in {"new", "assigned", "contacted"}
            and _hours_since(getattr(row, "last_action_at", None) or getattr(row, "updated_at", None) or getattr(row, "created_at", None)) > 24
        ]),
        "data_quality_alerts": len([
            row for row in results
            if (not getattr(row, "email", None) and not getattr(row, "phone", None))
            or (not getattr(row, "contact_name", None) and not getattr(row, "email", None))
        ]),
        "contacted_today": len([
            row for row in results
            if getattr(row, "queue_status", "") == "contacted"
            and getattr(row, "follow_up_at", None)
            and row.follow_up_at.date() == datetime.now(timezone.utc).date()
        ]),
        "workflow_failures": len([row for row in results if getattr(row, "error", None) or getattr(row, "follow_up_status", "") == "failed"]),
    }
    response_times = [
        (row.follow_up_at - row.created_at).total_seconds() / 60
        for row in results
        if getattr(row, "follow_up_at", None) and getattr(row, "created_at", None)
    ]
    summary["average_response_minutes"] = round(sum(response_times) / len(response_times)) if response_times else 0

    now = datetime.now(timezone.utc)
    today = now.date()
    yesterday = today - timedelta(days=1)
    intake_today = len([
        row for row in monitoring_rows
        if getattr(row, "created_at", None) and row.created_at.date() == today
    ])
    intake_yesterday = len([
        row for row in monitoring_rows
        if getattr(row, "created_at", None) and row.created_at.date() == yesterday
    ])
    no_contact_rows = [
        row for row in monitoring_rows
        if getattr(row, "queue_status", "new") in {"new", "assigned"}
        and not getattr(row, "follow_up_at", None)
    ]
    no_contact_aging = {
        "under_1_hour": len([row for row in no_contact_rows if _hours_since(getattr(row, "created_at", None)) < 1]),
        "one_to_four_hours": len([row for row in no_contact_rows if 1 <= _hours_since(getattr(row, "created_at", None)) < 4]),
        "four_to_twenty_four_hours": len([row for row in no_contact_rows if 4 <= _hours_since(getattr(row, "created_at", None)) < 24]),
        "over_24_hours": len([row for row in no_contact_rows if _hours_since(getattr(row, "created_at", None)) >= 24]),
    }
    source_groups: dict[str, list[Any]] = {}
    for row in monitoring_rows:
        source_groups.setdefault(getattr(row, "source", None) or "unknown", []).append(row)
    conversion_by_source = {
        source_name: {
            "total": len(source_rows),
            "contacted": len([row for row in source_rows if getattr(row, "queue_status", "new") in {"contacted", "qualified", "closed"}]),
            "qualified": len([row for row in source_rows if getattr(row, "queue_status", "new") in {"qualified", "closed"}]),
            "closed": len([row for row in source_rows if getattr(row, "queue_status", "new") == "closed"]),
            "conversion_percent": round(
                len([row for row in source_rows if getattr(row, "queue_status", "new") == "closed"]) / len(source_rows) * 100
            ) if source_rows else 0,
        }
        for source_name, source_rows in sorted(source_groups.items())
    }
    owner_groups: dict[str, list[Any]] = {}
    for row in monitoring_rows:
        owner_groups.setdefault(str(getattr(row, "assigned_user_id", None) or "unassigned"), []).append(row)
    owner_workload = [
        {
            "owner_id": owner_id,
            "total": len(owner_rows),
            "active": len([row for row in owner_rows if getattr(row, "queue_status", "new") != "closed"]),
            "stale": len([row for row in owner_rows if getattr(row, "queue_status", "new") in {"new", "assigned", "contacted"} and _hours_since(getattr(row, "last_action_at", None) or getattr(row, "created_at", None)) > 24]),
        }
        for owner_id, owner_rows in sorted(owner_groups.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    monitoring = {
        "generated_at": now.isoformat(),
        "lead_intake": {
            "today": intake_today,
            "yesterday": intake_yesterday,
            "change_percent": round((intake_today - intake_yesterday) / intake_yesterday * 100) if intake_yesterday else None,
        },
        "stale_leads": summary["stale_leads"],
        "no_contact_aging": no_contact_aging,
        "conversion_by_source": conversion_by_source,
        "owner_workload": owner_workload,
    }

    def alert(severity: str, code: str, message: str, count: int, action: str) -> dict[str, Any] | None:
        if count == 0:
            return None
        return {
            "severity": severity,
            "code": code,
            "message": message,
            "count": count,
            "action": action,
        }

    ownerless_count = summary["ownerless_leads"]
    stale_count = summary["stale_leads"]
    quality_count = summary["data_quality_alerts"]
    failure_count = summary["workflow_failures"]
    alerts = [
        alert("critical", "ownerless_hot_leads", "Hot leads have no owner.", ownerless_count, "Claim or assign each lead."),
        alert("warning", "stale_queue_work", "Queue work has exceeded its response window.", stale_count, "Review stale leads and record the next action."),
        alert("warning", "data_quality", "Leads are missing a usable contact channel.", quality_count, "Correct the contact record in GHL."),
        alert("critical", "workflow_failures", "Scoring or follow-up workflows need attention.", failure_count, "Review the error and retry when safe."),
    ]

    tracked_response_rows = [
        row for row in results
        if getattr(row, "follow_up_at", None) and getattr(row, "created_at", None)
    ]
    compliant_response_rows = [
        row for row in tracked_response_rows
        if 0 <= (row.follow_up_at - row.created_at).total_seconds() / 60
        <= SLA_RULES["assigned_contact_minutes"]
    ]
    response_compliance = round((len(compliant_response_rows) / len(tracked_response_rows)) * 100) if tracked_response_rows else 0

    queue_health = "healthy"
    if crm_status != "connected":
        queue_health = "degraded"
    elif summary["ownerless_leads"] > 0 or summary["stale_leads"] > 0 or summary["data_quality_alerts"] > 0:
        queue_health = "warning"
    if summary["workflow_failures"] > 0 and summary["stale_leads"] > 0:
        queue_health = "degraded"

    reporting = {
        "window": "current queue",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "response_compliance_percent": response_compliance,
        "average_response_minutes": summary["average_response_minutes"],
        "closed_leads": summary["closed"],
        "workflow_success_percent": round(
            ((summary["total"] - failure_count) / summary["total"]) * 100
        ) if summary["total"] else 100,
    }
    rollout = {
        "status": "ready" if queue_health == "healthy" else "needs_attention",
        "team": "Sales & Enrollment",
        "sop_route": "/dashboard/writer",
        "training_focus": "Claim leads, meet response SLAs, record next action, and resolve alerts.",
        "open_alerts": len([item for item in alerts if item]),
    }

    def next_action(row: BatchExecutionResult) -> str:
        if row.error or getattr(row, "follow_up_status", "") == "failed":
            return "Review error and retry"
        return {
            "new": "Claim lead",
            "assigned": "Contact lead",
            "contacted": "Qualify lead",
            "qualified": "Close lead",
            "closed": "Complete",
        }.get(getattr(row, "queue_status", "new"), "Review lead")

    def retry_available(row: BatchExecutionResult) -> bool:
        return row.status == "failed"

    return {
        "summary": summary,
        "health": {
            "queue_health": queue_health,
            "crm_status": crm_status,
            "contacts_checked": len(contacts),
            "ownerless_leads": summary["ownerless_leads"],
            "stale_leads": summary["stale_leads"],
            "data_quality_alerts": summary["data_quality_alerts"],
        },
        "sla": {
            "rules": SLA_RULES,
            "alerts": [item for item in alerts if item],
        },
        "reporting": reporting,
        "monitoring": monitoring,
        "rollout": rollout,
        "results": [
            {
                "id": str(row.id),
                "contact_id": row.contact_id,
                "contact_name": row.contact_name,
                "email": row.email,
                "phone": row.phone,
                "source": row.source,
                "score": row.score,
                "category": row.category,
                "execution_status": row.status,
                "queue_status": getattr(row, "queue_status", "new"),
                "assigned_user_id": str(row.assigned_user_id) if getattr(row, "assigned_user_id", None) else None,
                "follow_up_status": getattr(row, "follow_up_status", "not_started"),
                "follow_up_at": _serialize_datetime(getattr(row, "follow_up_at", None)),
                "lifecycle_stage": getattr(row, "lifecycle_stage", "not_started"),
                "next_step": getattr(row, "next_step", None),
                "response_at": _serialize_datetime(getattr(row, "response_at", None)),
                "booked_at": _serialize_datetime(getattr(row, "booked_at", None)),
                "enrollment_outcome": getattr(row, "enrollment_outcome", None),
                "error": row.error,
                "retry_count": row.retry_count,
                "score_origin": getattr(row, "score_origin", "approved_batch"),
                "notification_status": getattr(row, "notification_status", "not_attempted"),
                "notification_error": getattr(row, "notification_error", None),
                "last_action_at": _serialize_datetime(getattr(row, "last_action_at", None) or getattr(row, "updated_at", None) or row.created_at),
                "retry_available": retry_available(row),
                "operating_decision": getattr(row, "operating_decision", "hold"),
                "failure_class": getattr(row, "failure_class", None),
                "recovery_owner_id": str(row.recovery_owner_id) if getattr(row, "recovery_owner_id", None) else None,
                "recovery_status": getattr(row, "recovery_status", "unassigned"),
                "next_action": next_action(row),
                "ghl_contact_reference": row.contact_id,
                "created_at": _serialize_datetime(row.created_at),
            }
            for row in results
        ],
        "audit_events": [
            {
                "id": str(event.id),
                "result_id": str(event.result_id) if event.result_id else None,
                "event_type": event.event_type,
                "details": event.details,
                "created_at": _serialize_datetime(event.created_at),
            }
            for event in audits
        ],
    }


@router.patch("/batch-results/{result_id}/decision", dependencies=[Depends(require_permission("leads:write"))])
async def decide_batch_result(
    result_id: UUID,
    request: BatchDecisionRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Record the operator decision for a failed result without executing external work."""
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch result not found")

    approval = db.query(CohortApproval).filter(
        CohortApproval.id == result.approval_id,
        CohortApproval.user_id == current_user.id,
    ).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval record not found")
    if result.status not in {"failed", "missing_in_ghl", "held", "escalated", "exhausted"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed batch results can receive a recovery decision")
    if request.decision == "rerun" and result.status == "exhausted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maximum retry attempts reached; escalate this result")

    pending_retry = db.query(BatchRetry).filter(
        BatchRetry.result_id == result.id,
        BatchRetry.status.in_(["retry_pending", "held", "escalated"]),
    ).order_by(BatchRetry.created_at.desc()).first()
    if request.decision == "rerun" and not pending_retry:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No retry record is available for this result")

    result.operating_decision = request.decision
    result.failure_class = request.failure_class or getattr(result, "failure_class", None) or "unknown"
    result.recovery_owner_id = current_user.id
    result.recovery_status = "assigned" if request.decision == "rerun" else request.decision
    result.last_action_at = datetime.now(timezone.utc)
    if request.decision == "hold":
        result.status = "held"
    elif request.decision == "escalate":
        result.status = "escalated"
    if pending_retry:
        pending_retry.operating_decision = request.decision
        pending_retry.failure_class = result.failure_class
        pending_retry.recovery_owner_id = current_user.id
        pending_retry.status = "retry_pending" if request.decision == "rerun" else request.decision
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=result.id,
        event_type="batch_recovery_decision",
        details={
            "decision": request.decision,
            "failure_class": result.failure_class,
            "reason": request.reason,
            "recovery_owner_id": str(current_user.id),
        },
    ))
    db.commit()
    return {
        "status": result.status,
        "result_id": str(result.id),
        "decision": result.operating_decision,
        "failure_class": result.failure_class,
        "recovery_owner_id": str(result.recovery_owner_id),
    }


@router.post("/batch-results/{result_id}/retry", dependencies=[Depends(require_permission("leads:write"))])
async def retry_enrollment_batch_result(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retry one failed result from its original, user-owned approved cohort."""
    result = db.query(BatchExecutionResult).filter(
        BatchExecutionResult.id == result_id,
    ).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch result not found")

    approval = db.query(CohortApproval).filter(
        CohortApproval.id == result.approval_id,
        CohortApproval.user_id == current_user.id,
    ).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval record not found")
    if getattr(approval, "decision", "approved") != "approved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The parent approval is not approved for recovery")
    if getattr(result, "operating_decision", "hold") != "rerun":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Record an explicit rerun decision before retrying")
    if result.status != "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed results can be retried")
    if str(result.contact_id) not in {str(contact_id) for contact_id in (approval.contact_ids or [])}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Contact is outside the original approved batch")

    pending_retry = db.query(BatchRetry).filter(
        BatchRetry.result_id == result.id,
        BatchRetry.status == "retry_pending",
    ).order_by(BatchRetry.created_at.desc()).first()
    if not pending_retry:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This batch result is not waiting for retry",
        )
    if getattr(pending_retry, "operating_decision", "hold") != "rerun":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The retry is not approved to run")
    if pending_retry.next_attempt_at and pending_retry.next_attempt_at > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Retry is scheduled for {pending_retry.next_attempt_at.isoformat()}",
        )

    return await retry_batch_result(result, approval, db)


@router.patch("/hot-leads/{result_id}/lifecycle", dependencies=[Depends(require_permission("leads:write"))])
async def update_follow_up_lifecycle(
    result_id: UUID,
    request: FollowUpLifecycleRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Record the next authenticated step in the Enrollment follow-up lifecycle."""
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hot lead not found")
    if not result.assigned_user_id or str(result.assigned_user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim the lead before updating follow-up")

    previous_stage = getattr(result, "lifecycle_stage", "not_started")
    if request.stage not in LIFECYCLE_STAGES or request.stage not in LIFECYCLE_TRANSITIONS.get(previous_stage, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid follow-up lifecycle transition: {previous_stage} -> {request.stage}",
        )

    now = datetime.now(timezone.utc)
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status=result.queue_status,
        owner_id=str(current_user.id),
        lifecycle_stage=request.stage,
        note=f"ENY Enrollment lifecycle changed to {request.stage}: {request.reason}",
    )
    if not writeback.get("success"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={
            "message": "Follow-up lifecycle was not changed because GHL write-back failed",
            "writeback": writeback,
        })

    result.lifecycle_stage = request.stage
    result.lifecycle_updated_at = now
    result.next_step = request.next_step
    result.enrollment_outcome = request.enrollment_outcome
    if request.stage == "responded":
        result.response_at = now
    if request.stage == "booked":
        result.booked_at = now
    if request.stage == "enrolled":
        result.enrollment_outcome = request.enrollment_outcome or "enrolled"
    if request.stage == "lost":
        result.enrollment_outcome = request.enrollment_outcome or "lost"

    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=result.id,
        event_type="follow_up_lifecycle_changed",
        details={
            "from": previous_stage,
            "to": request.stage,
            "reason": request.reason,
            "next_step": request.next_step,
            "enrollment_outcome": result.enrollment_outcome,
            "ghl_writeback": writeback,
        },
    ))
    db.commit()
    return {
        "result_id": str(result.id),
        "lifecycle_stage": result.lifecycle_stage,
        "next_step": result.next_step,
        "response_at": _serialize_datetime(result.response_at),
        "booked_at": _serialize_datetime(result.booked_at),
        "enrollment_outcome": result.enrollment_outcome,
        "ghl_writeback": writeback,
    }


@router.post("/hot-leads/{result_id}/claim", dependencies=[Depends(require_permission("leads:write"))])
async def claim_hot_lead(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Assign one hot lead to the authenticated Enrollment user."""
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Hot lead not found")
    if result.category != "hot" or result.queue_status == "closed":
        raise HTTPException(status_code=409, detail="Lead is not available for claiming")
    current_user_id = str(current_user.id)
    if result.assigned_user_id and str(result.assigned_user_id) != current_user_id:
        raise HTTPException(status_code=409, detail="Lead is already assigned to another Enrollment user")
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status="assigned",
        owner_id=current_user_id,
        note=f"ENY Enrollment lead assigned to owner {current_user_id}.",
    )
    if not writeback.get("success"):
        raise HTTPException(status_code=502, detail={
            "message": "Lead was not assigned because GHL write-back failed",
            "writeback": writeback,
        })
    previous_state = _transition_queue_state(result, "assigned", current_user.id, "Claimed for active enrollment follow-up")
    result.assigned_user_id = current_user.id
    _audit(db, current_user, result.id, "hot_lead_claimed", {
        "contact_id": result.contact_id,
        "from": previous_state,
        "to": result.queue_status,
        "reason": "Claimed for active enrollment follow-up",
        "ghl_writeback": writeback,
    })
    return {"status": result.queue_status, "result_id": str(result.id), "assigned_user_id": str(current_user.id)}


@router.patch("/hot-leads/{result_id}/state", dependencies=[Depends(require_permission("leads:write"))])
async def update_hot_lead_state(
    result_id: UUID,
    request: QueueStateRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Move an owned hot lead through the Enrollment queue state machine."""
    if request.state not in QUEUE_STATES:
        raise HTTPException(status_code=422, detail=f"Invalid queue state: {request.state}")
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Hot lead not found")
    if not result.assigned_user_id or str(result.assigned_user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Claim the lead before changing its state")
    previous_state = result.queue_status
    if request.state not in QUEUE_STATES or request.state not in QUEUE_TRANSITIONS.get(previous_state, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Invalid queue transition: {previous_state} -> {request.state}")
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status=request.state,
        owner_id=str(current_user.id),
        note=f"ENY Enrollment queue status changed to {request.state}: {request.reason}",
    )
    if not writeback.get("success"):
        raise HTTPException(status_code=502, detail={
            "message": "Queue state was not changed because GHL write-back failed",
            "writeback": writeback,
        })
    _transition_queue_state(result, request.state, current_user.id, request.reason)
    _audit(db, current_user, result.id, "hot_lead_state_changed", {
        "contact_id": result.contact_id,
        "actor_id": str(current_user.id),
        "from": previous_state,
        "to": request.state,
        "reason": request.reason,
        "ghl_writeback": writeback,
    })
    return {"status": result.queue_status, "result_id": str(result.id), "ghl_writeback": writeback}


@router.post("/hot-leads/{result_id}/follow-up", dependencies=[Depends(require_permission("leads:write"))])
async def follow_up_hot_lead(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Trigger the registered n8n follow-up workflow for an owned hot lead."""
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Hot lead not found")
    if not result.assigned_user_id or str(result.assigned_user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Claim the lead before triggering follow-up")
    previous_state = result.queue_status
    if previous_state != "assigned":
        raise HTTPException(status_code=409, detail="Follow-up requires an assigned lead")
    workflow = await N8NService().trigger_workflow("eny-enrollment-follow-up", {
        "contact_id": result.contact_id,
        "result_id": str(result.id),
        "approval_id": str(result.approval_id),
        "assigned_user_id": str(current_user.id),
        "source": result.source,
        "score": result.score,
        "category": result.category,
    })
    if workflow.get("status") != "success":
        result.follow_up_status = "failed"
        db.commit()
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Follow-up workflow could not complete",
                "workflow": workflow.get("workflow", "eny-enrollment-follow-up"),
                "error": workflow.get("error") or workflow.get("message") or "Unknown n8n error",
                "contact_id": result.contact_id,
            },
        )
    result.follow_up_status = "tagged"
    result.follow_up_at = datetime.now(timezone.utc)
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status="contacted",
        owner_id=str(current_user.id),
        lifecycle_stage="queued",
        note="ENY Enrollment follow-up completed and contact status synchronized.",
    )
    if not writeback.get("success"):
        result.follow_up_status = "failed"
        result.notification_error = writeback.get("error")
        db.commit()
        raise HTTPException(status_code=502, detail={
            "message": "Follow-up workflow completed but GHL write-back failed",
            "writeback": writeback,
        })
    _transition_queue_state(result, "contacted", current_user.id, "Follow-up workflow completed")
    result.last_action_at = result.follow_up_at
    result.lifecycle_stage = "queued"
    result.lifecycle_updated_at = result.follow_up_at
    result.notification_status = "sent" if workflow.get("notification_sent") is True else "failed" if workflow.get("notification_error") else "unknown"
    result.notification_error = workflow.get("notification_error")
    if result.notification_status == "sent":
        result.notification_sent_at = result.follow_up_at
    _audit(db, current_user, result.id, "follow_up_triggered", {
        "contact_id": result.contact_id,
        "workflow": "eny-enrollment-follow-up",
        "from": previous_state,
        "to": result.queue_status,
        "notification_sent": workflow.get("notification_sent"),
        "notification_error": workflow.get("notification_error"),
        "ghl_writeback": writeback,
    })
    notification_sent = workflow.get("notification_sent")
    notification_error = workflow.get("notification_error")
    if notification_sent is True:
        message = "GHL follow-up tag applied and enrollment email sent."
    elif notification_error:
        message = f"GHL follow-up tag applied, but enrollment email failed: {notification_error}"
    else:
        message = "GHL follow-up tag applied; email delivery status was not reported."
    return {
        "status": result.follow_up_status,
        "queue_status": result.queue_status,
        "workflow": workflow,
        "ghl_writeback": writeback,
        "message": message,
    }

@router.get("/pipeline", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_pipeline(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get enrollment pipeline data.
    Requires leads:read permission.
    """
    try:
        pipeline = await ghl_service.get_pipeline_data()
        opportunities = pipeline.get("opportunities", [])
        stages = pipeline.get("stages", [])
        pipeline_data = {
            "totalLeads": pipeline.get("total_leads", 0),
            "conversionRate": round(float(pipeline.get("conversion_rate", 0)) * 100, 2),
            "revenueForecast": pipeline.get("revenue_forecast", 0),
            "atRiskDeals": pipeline.get("at_risk_deals", 0),
        }
        return {"pipeline": pipeline_data, "stages": stages, "opportunities": opportunities}
    except Exception as e:
        logger.error(f"Error fetching enrollment pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pipeline: {str(e)}"
        )


@router.get("/quality", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_quality(
    current_user: Any = Depends(get_current_user),
):
    """Return read-only GHL normalization and deduplication findings."""
    contacts, inventory = await ghl_service.get_all_contacts()
    return {
        "quality": ghl_service.build_contact_quality_report(contacts),
        "crm": inventory,
    }


@router.get("/adoption-policy", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_adoption_policy(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Return the shared Sales & Enrollment process policy and weekly review data."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = db.query(BatchExecutionResult).filter(BatchExecutionResult.created_at >= since).all()
    audits = db.query(EnrollmentAudit).filter(EnrollmentAudit.created_at >= since).all()
    lifecycle_counts: dict[str, int] = {}
    for row in rows:
        stage = getattr(row, "lifecycle_stage", "not_started")
        lifecycle_counts[stage] = lifecycle_counts.get(stage, 0) + 1
    return {
        "policy": OPERATING_POLICY,
        "review_window": {"days": 7, "since": since.isoformat(), "generated_at": datetime.now(timezone.utc).isoformat()},
        "weekly_review": {
            "results_created": len(rows),
            "audit_events": len(audits),
            "lifecycle_counts": lifecycle_counts,
            "closed_or_enrolled": len([row for row in rows if getattr(row, "queue_status", "") == "closed" or getattr(row, "lifecycle_stage", "") == "enrolled"]),
            "open_escalations": len([row for row in rows if getattr(row, "status", "") == "escalated"]),
            "stale_active_work": len([row for row in rows if getattr(row, "queue_status", "new") in {"new", "assigned", "contacted"} and _hours_since(getattr(row, "last_action_at", None) or getattr(row, "created_at", None)) > 24]),
        },
    }