# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/enrollment.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
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


class QueueStateRequest(BaseModel):
    state: str = Field(..., min_length=1, max_length=30)
    reason: Optional[str] = Field(None, max_length=500)


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
    audits = db.query(EnrollmentAudit).order_by(
        EnrollmentAudit.created_at.desc()
    ).limit(limit).all()
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
                "error": row.error,
                "retry_count": row.retry_count,
                "score_origin": getattr(row, "score_origin", "approved_batch"),
                "notification_status": getattr(row, "notification_status", "not_attempted"),
                "notification_error": getattr(row, "notification_error", None),
                "last_action_at": _serialize_datetime(getattr(row, "last_action_at", None) or getattr(row, "updated_at", None) or row.created_at),
                "retry_available": retry_available(row),
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
    if pending_retry.next_attempt_at and pending_retry.next_attempt_at > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Retry is scheduled for {pending_retry.next_attempt_at.isoformat()}",
        )

    return await retry_batch_result(result, approval, db)


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
    result.assigned_user_id = current_user.id
    result.queue_status = "assigned"
    result.last_action_at = datetime.now(timezone.utc)
    _audit(db, current_user, result.id, "hot_lead_claimed", {"contact_id": result.contact_id})
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
    if request.state not in QUEUE_TRANSITIONS.get(previous_state, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid queue transition: {previous_state} -> {request.state}",
        )
    result.queue_status = request.state
    result.last_action_at = datetime.now(timezone.utc)
    _audit(db, current_user, result.id, "hot_lead_state_changed", {
        "contact_id": result.contact_id,
        "actor_id": str(current_user.id),
        "from": previous_state,
        "to": request.state,
        "reason": request.reason,
    })
    return {"status": result.queue_status, "result_id": str(result.id)}


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
    result.queue_status = "contacted"
    result.last_action_at = result.follow_up_at
    result.notification_status = "sent" if workflow.get("notification_sent") is True else "failed" if workflow.get("notification_error") else "unknown"
    result.notification_error = workflow.get("notification_error")
    if result.notification_status == "sent":
        result.notification_sent_at = result.follow_up_at
    _audit(db, current_user, result.id, "follow_up_triggered", {
        "contact_id": result.contact_id,
        "workflow": "eny-enrollment-follow-up",
        "notification_sent": workflow.get("notification_sent"),
        "notification_error": workflow.get("notification_error"),
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