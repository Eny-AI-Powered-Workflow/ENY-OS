# C:\Users\Melody\Documents\ENY-OS\backend\app\api\v1\endpoints\business_support.py
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.business_support_pilot_review import BusinessSupportPilotReview
from app.models.payment_verification_event import PaymentVerificationEvent
from app.services.student_payments_service import student_payments_service
from app.services.workflow_registry import APPROVED_WORKFLOWS

router = APIRouter()
PilotScenario = Literal[
    "shadow_output",
    "provider_unavailable",
    "malformed_or_duplicate_webhook",
    "delayed_payment_evidence",
    "missing_recording",
    "rejected_action",
]
PilotWorkflow = Literal["eny-prog-onboard", "eny-prog-monitor"]
PilotResult = Literal["expected", "unexpected", "not_run"]


class PilotReviewCreate(BaseModel):
    id: UUID
    scenario: PilotScenario
    workflow_name: PilotWorkflow | None = None
    result: PilotResult
    false_positive: bool | None = None
    missing_data: bool | None = None
    processing_seconds: int | None = Field(default=None, ge=0, le=604800)
    escalation_quality: int | None = Field(default=None, ge=1, le=5)


class PaystackPaymentVerificationCreate(BaseModel):
    reference: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9.=-]+$")
    idempotency_key: UUID


@router.get("/overview", dependencies=[Depends(require_permission("business_support:dashboard:read"))])
async def get_business_support_overview() -> dict[str, Any]:
    """Return read-only workspace metadata without duplicating provider records."""
    return {
        "department": "Business Support",
        "mode": "read_only",
        "available_views": ["payment_records"],
        "notice": "Provider-reported payment records only. Verify decisions in the system of record.",
    }


def _serialize_pilot_review(review: BusinessSupportPilotReview) -> dict[str, Any]:
    return {
        "id": str(review.id),
        "scenario": review.scenario,
        "workflow_name": review.workflow_name,
        "result": review.result,
        "false_positive": review.false_positive,
        "missing_data": review.missing_data,
        "processing_seconds": review.processing_seconds,
        "escalation_quality": review.escalation_quality,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }


def _matches_pilot_review(review: BusinessSupportPilotReview, payload: PilotReviewCreate) -> bool:
    return all(
        getattr(review, field) == getattr(payload, field)
        for field in (
            "scenario",
            "workflow_name",
            "result",
            "false_positive",
            "missing_data",
            "processing_seconds",
            "escalation_quality",
        )
    )


def _reviewer_id(current_user: Any) -> UUID:
    return current_user.get("id") if isinstance(current_user, dict) else current_user.id


def _serialize_payment_verification(event: PaymentVerificationEvent) -> dict[str, Any]:
    return {
        "reference": event.transaction_reference,
        "verification_status": event.verification_status,
        "provider_status": event.provider_status,
        "reviewer_id": str(event.reviewer_user_id),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def _same_payment_verification(event: PaymentVerificationEvent, reference: str, reviewer_id: UUID) -> bool:
    return (
        event.provider == "paystack"
        and event.transaction_reference == reference
        and event.reviewer_user_id == reviewer_id
    )


@router.get("/payments/verification-status", dependencies=[Depends(require_permission("payments:verify"))])
def get_payment_verification_status(
    references: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    unique_references = list(dict.fromkeys(references))
    if len(unique_references) > 100 or any(
        not 1 <= len(reference) <= 100 or not all(char.isalnum() or char in ".=-" for char in reference)
        for reference in unique_references
    ):
        raise HTTPException(status_code=422, detail="Invalid Paystack transaction references")
    if not unique_references:
        return {"verifications": {}}

    events = (
        db.query(PaymentVerificationEvent)
        .filter(PaymentVerificationEvent.provider == "paystack")
        .filter(PaymentVerificationEvent.transaction_reference.in_(unique_references))
        .order_by(PaymentVerificationEvent.created_at.desc())
        .limit(500)
        .all()
    )
    latest: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.transaction_reference not in latest:
            latest[event.transaction_reference] = _serialize_payment_verification(event)
    return {"verifications": latest}


@router.post("/payments/verify", dependencies=[Depends(require_permission("payments:verify"))])
async def verify_paystack_payment(
    payload: PaystackPaymentVerificationCreate,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    reviewer_id = UUID(str(_reviewer_id(current_user)))
    existing = (
        db.query(PaymentVerificationEvent)
        .filter(PaymentVerificationEvent.idempotency_key == payload.idempotency_key)
        .first()
    )
    if existing:
        if _same_payment_verification(existing, payload.reference, reviewer_id):
            return {"verification": _serialize_payment_verification(existing), "duplicate": True}
        raise HTTPException(status_code=409, detail="This payment verification request ID was already used")

    provider_result = await student_payments_service.verify_paystack_transaction(payload.reference)
    event = PaymentVerificationEvent(
        provider="paystack",
        transaction_reference=payload.reference,
        verification_status=provider_result["verification_status"],
        provider_status=provider_result["provider_status"],
        reviewer_user_id=reviewer_id,
        idempotency_key=payload.idempotency_key,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(PaymentVerificationEvent)
            .filter(PaymentVerificationEvent.idempotency_key == payload.idempotency_key)
            .first()
        )
        if existing and _same_payment_verification(existing, payload.reference, reviewer_id):
            return {"verification": _serialize_payment_verification(existing), "duplicate": True}
        raise HTTPException(status_code=409, detail="This payment verification request ID was already used") from exc
    db.refresh(event)
    return {"verification": _serialize_payment_verification(event), "duplicate": False}


@router.get("/pilot/reviews", dependencies=[Depends(require_permission("business_support:pilot:read"))])
def get_pilot_reviews(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    reviews = (
        db.query(BusinessSupportPilotReview)
        .filter(BusinessSupportPilotReview.created_at >= cutoff)
        .order_by(BusinessSupportPilotReview.created_at.desc())
        .limit(500)
        .all()
    )
    reviewed = [review for review in reviews if review.result != "not_run"]
    processing_samples = [review.processing_seconds for review in reviewed if review.processing_seconds is not None]
    escalation_samples = [review.escalation_quality for review in reviews if review.escalation_quality is not None]
    return {
        "days": days,
        "truncated": len(reviews) == 500,
        "summary": {
            "total_reviews": len(reviews),
            "expected": sum(review.result == "expected" for review in reviews),
            "unexpected": sum(review.result == "unexpected" for review in reviews),
            "not_run": sum(review.result == "not_run" for review in reviews),
            "false_positive_samples": sum(review.false_positive is True for review in reviews),
            "missing_data_samples": sum(review.missing_data is True for review in reviews),
            "average_processing_seconds": round(sum(processing_samples) / len(processing_samples), 2) if processing_samples else None,
            "average_escalation_quality": round(sum(escalation_samples) / len(escalation_samples), 2) if escalation_samples else None,
        },
        "reviews": [_serialize_pilot_review(review) for review in reviews],
    }


@router.post("/pilot/reviews", dependencies=[Depends(require_permission("business_support:pilot:write"))])
def create_pilot_review(
    payload: PilotReviewCreate,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    if payload.scenario == "shadow_output":
        workflow = APPROVED_WORKFLOWS.get(payload.workflow_name or "")
        if not workflow or workflow.get("mode") != "shadow":
            raise HTTPException(status_code=422, detail="Choose a workflow currently approved for shadow mode")
    elif payload.workflow_name:
        raise HTTPException(status_code=422, detail="Workflow names are only accepted for shadow-output reviews")

    reviewer_id = _reviewer_id(current_user)
    existing = db.query(BusinessSupportPilotReview).filter(BusinessSupportPilotReview.id == payload.id).first()
    if existing:
        if existing.reviewer_user_id == reviewer_id and _matches_pilot_review(existing, payload):
            return {"review": _serialize_pilot_review(existing), "duplicate": True}
        raise HTTPException(status_code=409, detail="This pilot review ID was already used")

    review = BusinessSupportPilotReview(
        id=payload.id,
        scenario=payload.scenario,
        workflow_name=payload.workflow_name,
        result=payload.result,
        false_positive=payload.false_positive,
        missing_data=payload.missing_data,
        processing_seconds=payload.processing_seconds,
        escalation_quality=payload.escalation_quality,
        reviewer_user_id=reviewer_id,
    )
    db.add(review)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.query(BusinessSupportPilotReview).filter(BusinessSupportPilotReview.id == payload.id).first()
        if existing and existing.reviewer_user_id == reviewer_id and _matches_pilot_review(existing, payload):
            return {"review": _serialize_pilot_review(existing), "duplicate": True}
        raise HTTPException(status_code=409, detail="This pilot review ID was already used") from exc
    db.refresh(review)
    return {"review": _serialize_pilot_review(review), "duplicate": False}