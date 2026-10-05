# C:/Users/Melody/Documents/ENY-OS/backend/app/api/v1/endpoints/calendar.py
from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.services.ea_coordination_service import ea_coordination_service

router = APIRouter()


@router.get("/coordination", dependencies=[Depends(require_permission("calendar:read"))])
async def get_calendar_coordination():
    """Read upcoming events and open tasks from the shared Google account."""
    return await ea_coordination_service.get_coordination()
