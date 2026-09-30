# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/student_success.py
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import require_permission
from app.services.student_lifecycle_service import student_lifecycle_service
from app.services.student_payments_service import student_payments_service
from app.services.student_success_service import student_success_service

router = APIRouter()


@router.get("/offers", dependencies=[Depends(require_permission("students:read"))])
async def get_student_success_offers(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=100),
):
    return await student_success_service.list_offers(page, per_page)


@router.get("/students", dependencies=[Depends(require_permission("students:read"))])
async def get_student_list(
    offer_id: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    return await student_success_service.list_students(offer_id, page, limit, search)


@router.get("/progress", dependencies=[Depends(require_permission("students:read"))])
async def get_student_progress(offer_id: str = Query(..., min_length=1)):
    return await student_success_service.get_progress(offer_id)


@router.get("/metrics", dependencies=[Depends(require_permission("students:read"))])
async def get_student_success_metrics(offer_id: str = Query(..., min_length=1)):
    return await student_success_service.get_metrics(offer_id)


def _validate_date_range(from_date: date | None, to_date: date | None) -> None:
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be on or before to_date")


@router.get("/payments/kajabi", dependencies=[Depends(require_permission("payments:kajabi:read"))])
async def get_kajabi_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    from_date: date | None = None,
    to_date: date | None = None,
):
    _validate_date_range(from_date, to_date)
    return await student_payments_service.list_kajabi_transactions(page, per_page, from_date, to_date)


@router.get("/payments/paystack", dependencies=[Depends(require_permission("payments:paystack:read"))])
async def get_paystack_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    from_date: date | None = None,
    to_date: date | None = None,
):
    _validate_date_range(from_date, to_date)
    return await student_payments_service.list_paystack_transactions(page, per_page, from_date, to_date)


class LifecycleQueueItemCreate(BaseModel):
    workflow: str = Field(..., min_length=1)
    student_name: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    status: str = "queued"
    owner: str = "customer_success"


class LifecycleQueueItemUpdate(BaseModel):
    status: str = Field(..., min_length=1)


class CommunicationDraftCreate(BaseModel):
    student_name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class PaymentVerificationRequestCreate(BaseModel):
    student_name: str = Field(..., min_length=1)
    amount: str = Field(..., min_length=1)


@router.get("/lifecycle/queue", dependencies=[Depends(require_permission("students:read"))])
async def get_lifecycle_queue():
    return student_lifecycle_service.get_queue()


@router.post("/lifecycle/queue", dependencies=[Depends(require_permission("students:attendance:write"))])
async def create_lifecycle_queue_item(payload: LifecycleQueueItemCreate):
    return student_lifecycle_service.create_queue_item(
        workflow=payload.workflow,
        student_name=payload.student_name,
        summary=payload.summary,
        status=payload.status,
        owner=payload.owner,
    )


@router.patch("/lifecycle/queue/{item_id}/status", dependencies=[Depends(require_permission("students:attendance:write"))])
async def update_lifecycle_queue_item(item_id: str, payload: LifecycleQueueItemUpdate):
    return student_lifecycle_service.update_queue_item(item_id=item_id, status=payload.status)


@router.get("/lifecycle/drafts", dependencies=[Depends(require_permission("students:intervention:review"))])
async def get_lifecycle_drafts():
    return student_lifecycle_service.get_drafts()


@router.post("/lifecycle/drafts", dependencies=[Depends(require_permission("students:intervention:review"))])
async def create_lifecycle_draft(payload: CommunicationDraftCreate):
    return student_lifecycle_service.create_communication_draft(
        student_name=payload.student_name,
        category=payload.category,
        message=payload.message,
    )


@router.patch("/lifecycle/drafts/{draft_id}/approve", dependencies=[Depends(require_permission("students:intervention:approve"))])
async def approve_lifecycle_draft(draft_id: str):
    return student_lifecycle_service.approve_communication_draft(draft_id, permission_scope="students:intervention:approve")


@router.get("/lifecycle/payment-verification", dependencies=[Depends(require_permission("payments:verify"))])
async def get_payment_verification_requests():
    return student_lifecycle_service.get_payment_verification_requests()


@router.post("/lifecycle/payment-verification", dependencies=[Depends(require_permission("students:attendance:write"))])
async def create_payment_verification_request(payload: PaymentVerificationRequestCreate):
    return student_lifecycle_service.create_payment_verification_request(
        student_name=payload.student_name,
        amount=payload.amount,
    )


@router.patch("/lifecycle/payment-verification/{request_id}/status", dependencies=[Depends(require_permission("payments:verify"))])
async def update_payment_verification_request(request_id: str, payload: LifecycleQueueItemUpdate):
    return student_lifecycle_service.update_payment_verification_status(
        request_id=request_id,
        status=payload.status,
        permission_scope="payments:verify",
    )