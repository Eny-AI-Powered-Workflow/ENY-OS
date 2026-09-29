# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/student_success.py
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import require_permission
from app.services.student_payments_service import student_payments_service

router = APIRouter()


def _source_unavailable(source: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={"code": "source_not_configured", "source": source},
    )


@router.get("/metrics", dependencies=[Depends(require_permission("students:read"))])
async def get_student_success_metrics() -> None:
    raise _source_unavailable("student_lifecycle")


@router.get("/students", dependencies=[Depends(require_permission("students:read"))])
async def get_student_list(
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    risk: str | None = None,
) -> None:
    raise _source_unavailable("student_lifecycle")


@router.get("/progress", dependencies=[Depends(require_permission("students:read"))])
async def get_student_progress() -> None:
    raise _source_unavailable("student_lifecycle")


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