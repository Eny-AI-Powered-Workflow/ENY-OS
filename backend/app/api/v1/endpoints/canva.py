# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/canva.py

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
from app.models.design_system import DesignProviderEvent
from app.services.canva_service import canva_service

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


def _post_connect_redirect(request: Request) -> str:
    origin = request.headers.get("origin", "").rstrip("/")
    if not _approved_frontend_origin(origin):
        raise HTTPException(status_code=400, detail="Canva must be connected from an approved frontend origin")
    return f"{origin}/canva/oauth-complete"


def _oauth_completion_url(redirect_url: str, status: str) -> str:
    candidate = urlsplit(redirect_url)
    origin = f"{candidate.scheme}://{candidate.netloc}"
    if not _approved_frontend_origin(origin):
        fallback = urlsplit(settings.CANVA_POST_CONNECT_REDIRECT)
        origin = f"{fallback.scheme}://{fallback.netloc}"
    if not _approved_frontend_origin(origin):
        raise HTTPException(status_code=500, detail="Canva OAuth completion frontend origin is not configured")
    return f"{origin}/canva/oauth-complete?canva={status}"


@router.get("/status", dependencies=[Depends(require_permission("design:canva"))])
async def get_canva_status(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    return canva_service.connection_status(db, current_user.id)


@router.post("/connect", dependencies=[Depends(require_permission("design:canva"))])
async def start_canva_connection(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, str]:
    authorization_url = canva_service.authorization_url(
        db,
        current_user.id,
        _post_connect_redirect(request),
    )
    db.add(DesignProviderEvent(
        provider="canva",
        entity_type="oauth",
        actor_id=current_user.id,
        event_type="authorization_started",
        status="pending",
        details={},
    ))
    db.commit()
    return {"authorization_url": authorization_url, "status": "authorization_required"}


@router.get("/oauth/callback")
async def complete_canva_connection(
    code: str = Query(..., min_length=8),
    state: str = Query(..., min_length=16),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    user_id, post_connect_redirect = await canva_service.complete_authorization(db, code, state)
    db.add(DesignProviderEvent(
        provider="canva",
        entity_type="oauth",
        actor_id=user_id,
        event_type="connected",
        status="success",
        details={},
    ))
    db.commit()
    redirect_url = post_connect_redirect or settings.CANVA_POST_CONNECT_REDIRECT
    return RedirectResponse(url=_oauth_completion_url(redirect_url, "connected"), status_code=303)


@router.post("/disconnect", dependencies=[Depends(require_permission("design:canva"))])
async def disconnect_canva(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, str]:
    await canva_service.revoke(db, current_user.id)
    db.add(DesignProviderEvent(
        provider="canva",
        entity_type="oauth",
        actor_id=current_user.id,
        event_type="disconnected",
        status="success",
        details={},
    ))
    db.commit()
    return {"status": "disconnected"}
