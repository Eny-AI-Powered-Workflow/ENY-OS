# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/enrollment.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session
import logging
from uuid import UUID

from app.models.batch_execution_result import BatchExecutionResult
from app.models.batch_retry import BatchRetry
from app.models.cohort_approval import CohortApproval
from app.services.batch_execution_service import retry_batch_result

router = APIRouter()
logger = logging.getLogger(__name__)


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
        metrics = {
            "totalLeads": 1542,
            "newLeadsToday": 23,
            "conversionRate": 18.5,
            "revenuePipeline": 425000
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
        # Mock data
        leads = []
        for i in range(min(limit, 10)):  # Return up to 10 mock leads
            leads.append({
                "id": f"lead_{i+1}",
                "firstName": f"FirstName{i+1}",
                "lastName": f"LastName{i+1}",
                "email": f"lead{i+1}@example.com",
                "phone": f"555-000-{i+1:04d}",
                "score": 75 + (i * 2) % 25,
                "tags": ["hot"] if i % 3 == 0 else ["warm"] if i % 3 == 1 else ["follow-up"]
            })
        return {"leads": leads}
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

        rows = (
            db.query(BatchExecutionResult)
            .filter(BatchExecutionResult.status.in_(["scored", "queued", "hot"]))
            .filter(BatchExecutionResult.category == "hot")
            .filter(BatchExecutionResult.score >= min_score)
            .order_by(BatchExecutionResult.created_at.desc())
            .limit(limit)
            .all()
        )

        leads = [
            {
                "id": str(row.contact_id),
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
                "status": row.status,
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
        return {"results": results, "total": len(results), "limit": limit}
    except Exception as e:
        logger.error(f"Error fetching batch execution results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch batch execution results: {str(e)}",
        )


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

    return await retry_batch_result(result, approval, db)

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
        pipeline_data = {
            "totalLeads": 1542,
            "conversionRate": 18.5,
            "revenueForecast": 425000,
            "atRiskDeals": 45
        }
        stages = [
            {"id": "1", "name": "New Lead", "description": "Recently acquired leads", "count": 320, "percentage": 20.7, "color": "gray"},
            {"id": "2", "name": "Contacted", "description": "Initial contact made", "count": 280, "percentage": 18.2, "color": "blue"},
            {"id": "3", "name": "Qualified", "description": "Meets basic criteria", "count": 250, "percentage": 16.2, "color": "green"},
            {"id": "4", "name": "Proposal Sent", "description": "Proposal/quote sent", "count": 180, "percentage": 11.7, "color": "yellow"},
            {"id": "5", "name": "Negotiation", "description": "Price/terms negotiation", "count": 120, "percentage": 7.8, "color": "orange"},
            {"id": "6", "name": "Closed Won", "description": "Successfully converted", "count": 285, "percentage": 18.5, "color": "green"},
            {"id": "7", "name": "Closed Lost", "description": "Did not convert", "count": 307, "percentage": 19.9, "color": "red"}
        ]
        return {"pipeline": pipeline_data, "stages": stages}
    except Exception as e:
        logger.error(f"Error fetching enrollment pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pipeline: {str(e)}"
        )