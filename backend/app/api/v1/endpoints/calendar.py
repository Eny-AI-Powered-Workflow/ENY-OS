# C:/Users/Melody/Documents/ENY-OS/backend/app/api/v1/endpoints/calendar.py
import re
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.services.ea_coordination_service import ea_coordination_service

router = APIRouter()


def _approved_frontend_origin(origin: str) -> bool:
    parsed_origin = urlsplit(origin)
    allowed = origin in settings.cors_origins
    if not allowed and settings.cors_origin_regex:
        allowed = re.fullmatch(settings.cors_origin_regex, origin) is not None
    return bool(
        allowed
        and parsed_origin.scheme in {"https", "http"}
        and parsed_origin.netloc
        and not parsed_origin.path
        and not parsed_origin.query
        and not parsed_origin.fragment
        and not parsed_origin.username
        and not parsed_origin.password
        and (parsed_origin.scheme == "https" or parsed_origin.hostname in {"localhost", "127.0.0.1"})
    )


def _oauth_completion_url(origin: str, status: str) -> str:
    if not _approved_frontend_origin(origin):
        raise HTTPException(status_code=400, detail="Google Calendar OAuth origin is not approved")
    return f"{origin}/dashboard/calendar?google_calendar={status}"


@router.get("/connection", dependencies=[Depends(require_permission("calendar:manage"))])
async def get_calendar_connection(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return ea_coordination_service.connection_status(db)


@router.post("/connect", dependencies=[Depends(require_permission("calendar:manage"))])
async def start_calendar_connection(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, str]:
    origin = request.headers.get("origin", "").rstrip("/")
    if not _approved_frontend_origin(origin):
        raise HTTPException(status_code=400, detail="Connect Google Calendar from an approved frontend origin")
    return {
        "authorization_url": ea_coordination_service.authorization_url(db, current_user.id, origin),
        "status": "authorization_required",
    }


@router.get("/oauth/callback")
async def complete_calendar_connection(
    state: str = Query(..., min_length=16),
    code: str | None = Query(default=None, min_length=1),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if error:
        origin = ea_coordination_service.consume_denied_authorization(db, state)
        return RedirectResponse(url=_oauth_completion_url(origin, "denied"), status_code=303)
    if not code:
        raise HTTPException(status_code=400, detail="Google authorization did not return a code")
    origin = await ea_coordination_service.complete_authorization(db, code, state)
    return RedirectResponse(url=_oauth_completion_url(origin, "connected"), status_code=303)


@router.post("/disconnect", dependencies=[Depends(require_permission("calendar:manage"))])
async def disconnect_calendar(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return await ea_coordination_service.disconnect(db)


@router.get("/coordination", dependencies=[Depends(require_permission("calendar:read"))])
async def get_calendar_coordination(db: Session = Depends(get_db)):
    """Read events and tasks from the platform's connected Google account."""
    return await ea_coordination_service.get_coordination(db)
