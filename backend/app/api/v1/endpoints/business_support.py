# C:\Users\Melody\Documents\ENY-OS\backend\app\api\v1\endpoints\business_support.py
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_permission

router = APIRouter()


@router.get("/overview", dependencies=[Depends(require_permission("business_support:dashboard:read"))])
async def get_business_support_overview() -> dict[str, Any]:
    """Return read-only workspace metadata without duplicating provider records."""
    return {
        "department": "Business Support",
        "mode": "read_only",
        "available_views": ["payment_records"],
        "notice": "Provider-reported payment records only. Verify decisions in the system of record.",
    }