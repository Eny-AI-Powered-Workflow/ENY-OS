# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/batch_execution_service.py
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.models.batch_execution_result import BatchExecutionResult
from app.models.batch_retry import BatchRetry
from app.models.cohort_approval import CohortApproval
from app.models.enrollment_audit import EnrollmentAudit
from app.models.ghl_lead_intake import GHLLeadIntake
from app.models.operational_alert import OperationalAlert
from app.services.claude_service import ClaudeService
from app.services.ghl_service import ghl_service


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

    try:
        scoring = await ClaudeService().score_lead(lead_data)
    except Exception as exc:
        error = f"Lead scoring failed: {exc}"
        result.status = "failed"
        result.error = error
        result.retry_count = attempt_number
        result.failure_class = "workflow"
        result.operating_decision = "hold"
        result.recovery_status = "unassigned"
        db.add(BatchRetry(
            result_id=result.id,
            attempt_number=attempt_number,
            error_message=error,
            status="retry_pending" if attempt_number < settings.BATCH_MAX_RETRIES else "exhausted",
            next_attempt_at=next_attempt_at if attempt_number < settings.BATCH_MAX_RETRIES else None,
            failure_class="workflow",
            operating_decision="hold",
        ))
        db.add(OperationalAlert(
            alert_type="sales_scoring_failure",
            source="claude",
            message="Lead scoring retry failed and needs operator review.",
            result_id=result.id,
            details={"contact_id": result.contact_id, "approval_id": str(approval.id), "error": str(exc)},
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

    score = int(scoring["score"])
    category = derive_score_category(score)
    tags = list(dict.fromkeys((contact.get("tags") or []) + ["lead-scored", "approved-batch", category]))
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status=result.queue_status or "new",
        score=score,
        category=category,
        note=(
            f"ENY AI scoring: {category} ({score}/100). "
            f"{scoring['reasoning']} Next action: {scoring['next_best_action']}"
        ),
    )
    write_ok = bool(writeback.get("success"))

    result.retry_count = attempt_number
    if not write_ok:
        error = "GHL update failed"
        result.status = "failed"
        result.error = error
        result.notification_error = writeback.get("error")
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
    result.score_origin = "claude"
    result.score_reasoning = scoring["reasoning"]
    result.score_factors = scoring["score_factors"]
    result.score_evidence = scoring["evidence"]
    result.score_unknowns = scoring["unknowns"]
    result.next_best_action = scoring["next_best_action"]
    result.operating_decision = "complete"
    result.recovery_status = "resolved"
    result.email = contact.get("email")
    result.phone = contact.get("phone")
    result.source = contact.get("source") or "unknown"
    result.tags = tags
    result.queue_status = "new" if category == "hot" else result.queue_status
    result.follow_up_status = "not_started"
    if category == "hot":
        db.add(OperationalAlert(
            alert_type="hot_lead_ready",
            source="sales_scoring",
            severity="warning",
            message="A newly scored hot lead is ready for Sales & Enrollment review.",
            result_id=result.id,
            details={
                "contact_id": result.contact_id,
                "score": score,
                "category": category,
                "next_best_action": scoring["next_best_action"],
            },
        ))
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
                details={"contact_id": result.contact_id, "attempt_number": attempt_number, "writeback": writeback},
        ))
    intake_row = db.query(GHLLeadIntake).filter(
        GHLLeadIntake.contact_id == str(result.contact_id),
        GHLLeadIntake.approval_id == approval.id,
    ).with_for_update().first()
    if intake_row:
        intake_row.status = "scored"
    db.commit()

    return {
        "status": "scored",
        "result_id": str(result.id),
        "contact_id": result.contact_id,
        "score": score,
        "category": category,
        "retry_count": attempt_number,
        "score_origin": "claude",
        "score_reasoning": scoring["reasoning"],
        "score_factors": scoring["score_factors"],
        "score_evidence": scoring["evidence"],
        "score_unknowns": scoring["unknowns"],
        "next_best_action": scoring["next_best_action"],
        "ghl_writeback": writeback,
    }
