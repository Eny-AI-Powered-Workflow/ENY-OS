# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/batch_execution_service.py
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.models.batch_execution_result import BatchExecutionResult
from app.models.batch_retry import BatchRetry
from app.models.cohort_approval import CohortApproval
from app.models.enrollment_audit import EnrollmentAudit
from app.services.claude_service import ClaudeService
from app.services.ghl_service import ghl_service
from app.services.n8n_service import N8NService


def derive_score_category(score: int | float) -> str:
    if score >= 85:
        return "hot"
    if score >= 70:
        return "warm"
    if score >= 50:
        return "follow-up"
    return "cold"


async def retry_batch_result(
    result: BatchExecutionResult,
    approval: CohortApproval,
    db: Any,
) -> dict[str, Any]:
    """Retry one approved contact write in GHL and update its execution ledger row."""
    if int(result.retry_count or 0) >= settings.BATCH_MAX_RETRIES:
        result.status = "exhausted"
        result.error = "Maximum retry attempts reached"
        result.operating_decision = "escalate"
        result.recovery_status = "escalated"
        db.commit()
        return {
            "status": "exhausted",
            "result_id": str(result.id),
            "contact_id": result.contact_id,
            "retry_count": result.retry_count,
        }

    pending_retry = db.query(BatchRetry).filter(
        BatchRetry.result_id == result.id,
        BatchRetry.status == "retry_pending",
    ).order_by(BatchRetry.created_at.desc()).first()
    if pending_retry:
        pending_retry.status = "attempted"

    contact = await ghl_service.get_contact(str(result.contact_id))
    attempt_number = int(result.retry_count or 0) + 1
    retry_delay = settings.BATCH_RETRY_BACKOFF_SECONDS * (2 ** max(attempt_number - 1, 0))
    next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)

    if not contact:
        error = "Contact not found in GHL"
        result.status = "failed"
        result.error = error
        result.retry_count = attempt_number
        result.failure_class = "crm_contact_missing"
        result.operating_decision = "hold"
        result.recovery_status = "unassigned"
        db.add(BatchRetry(
            result_id=result.id,
            attempt_number=attempt_number,
            error_message=error,
            status="retry_pending" if attempt_number < settings.BATCH_MAX_RETRIES else "exhausted",
            next_attempt_at=next_attempt_at if attempt_number < settings.BATCH_MAX_RETRIES else None,
            failure_class="crm_contact_missing",
            operating_decision="hold",
        ))
        if attempt_number >= settings.BATCH_MAX_RETRIES:
            result.status = "exhausted"
        db.commit()
        return {
            "status": result.status,
            "result_id": str(result.id),
            "contact_id": result.contact_id,
            "error": error,
            "retry_count": attempt_number,
        }

    custom_fields = contact.get("customFields", [])
    if isinstance(custom_fields, dict):
        custom_fields = [custom_fields]
    lead_data = {
        "id": contact.get("id"),
        "name": contact.get("name") or " ".join(
            part for part in [contact.get("firstName"), contact.get("lastName")] if part
        ),
        "email": contact.get("email"),
        "phone": contact.get("phone"),
        "source": contact.get("source") or "unknown",
        "tags": contact.get("tags", []),
        "customFields": custom_fields,
    }

    workflow_result = await N8NService().trigger_workflow(
        "eny-sales-score",
        {
            "contact_id": str(result.contact_id),
            "lead_data": lead_data,
            "approval_id": str(approval.id),
            "source": lead_data["source"],
            "tags": lead_data["tags"],
        },
    )
    if workflow_result.get("status") == "success":
        score_value = workflow_result.get("score", 0)
        scoring = {
            "score": score_value,
            "category": derive_score_category(score_value),
            "tags": workflow_result.get("tags", []),
        }
    else:
        scoring = ClaudeService().deterministic_score_lead(lead_data)
        score_value = scoring.get("score", 50)

    try:
        score = int(score_value)
    except (TypeError, ValueError):
        score = 50
    category = scoring.get("category") or derive_score_category(score)
    tags = list(dict.fromkeys((contact.get("tags") or []) + ["lead-scored", "approved-batch", category]))
    write_ok = await ghl_service.update_contact(
        str(result.contact_id),
        {
            "customFields": [
                {"id": settings.GHL_SALES_SCORE_FIELD_ID, "value": score},
                {"id": settings.GHL_SCORE_CATEGORY_FIELD_ID, "value": category},
            ],
            "tags": tags,
        },
    )

    result.retry_count = attempt_number
    if not write_ok:
        error = "GHL update failed"
        result.status = "failed"
        result.error = error
        result.failure_class = "crm_write"
        result.operating_decision = "hold"
        result.recovery_status = "unassigned"
        db.add(BatchRetry(
            result_id=result.id,
            attempt_number=attempt_number,
            error_message=error,
            status="retry_pending" if attempt_number < settings.BATCH_MAX_RETRIES else "exhausted",
            next_attempt_at=next_attempt_at if attempt_number < settings.BATCH_MAX_RETRIES else None,
            failure_class="crm_write",
            operating_decision="hold",
        ))
        if attempt_number >= settings.BATCH_MAX_RETRIES:
            result.status = "exhausted"
        db.commit()
        return {
            "status": result.status,
            "result_id": str(result.id),
            "contact_id": result.contact_id,
            "error": error,
            "retry_count": attempt_number,
        }

    result.status = "scored"
    result.error = None
    result.score = score
    result.category = category
    result.score_origin = "n8n" if workflow_result.get("status") == "success" else "deterministic_fallback"
    result.operating_decision = "complete"
    result.recovery_status = "resolved"
    result.email = contact.get("email")
    result.phone = contact.get("phone")
    result.source = contact.get("source") or "unknown"
    result.tags = tags
    result.queue_status = "new" if category == "hot" else result.queue_status
    result.follow_up_status = "not_started"
    db.add(BatchRetry(
        result_id=result.id,
        attempt_number=attempt_number,
        error_message="Retry completed successfully",
        status="succeeded",
        operating_decision="rerun",
    ))
    if getattr(approval, "user_id", None):
        db.add(EnrollmentAudit(
            user_id=approval.user_id,
            result_id=result.id,
            event_type="retry_succeeded",
            details={"contact_id": result.contact_id, "attempt_number": attempt_number},
        ))
    db.commit()

    notification = None
    if category == "hot":
        notification = await N8NService().trigger_workflow(
            "eny-enrollment-hot-leads",
            {
                "contact_id": str(result.contact_id),
                "score": score,
                "category": category,
                "source": result.source,
                "tags": tags,
                "approval_id": str(approval.id),
            },
        )

    return {
        "status": "scored",
        "result_id": str(result.id),
        "contact_id": result.contact_id,
        "score": score,
        "category": category,
        "retry_count": attempt_number,
        "enrollment_notification": notification,
    }
