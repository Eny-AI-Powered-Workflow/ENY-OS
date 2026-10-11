# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/canva.py

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.design_system import DesignProviderEvent
from app.services.canva_service import canva_service

router = APIRouter()


@router.get("/status", dependencies=[Depends(require_permission("design:canva"))])
async def get_canva_status(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    return canva_service.connection_status(db, current_user.id)


@router.post("/connect", dependencies=[Depends(require_permission("design:canva"))])
async def start_canva_connection(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, str]:
    authorization_url = canva_service.authorization_url(db, current_user.id)
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
    user_id = await canva_service.complete_authorization(db, code, state)
    db.add(DesignProviderEvent(
        provider="canva",
        entity_type="oauth",
        actor_id=user_id,
        event_type="connected",
        status="success",
        details={},
    ))
    db.commit()
    redirect_url = settings.CANVA_POST_CONNECT_REDIRECT
    separator = "&" if "?" in redirect_url else "?"
    return RedirectResponse(url=f"{redirect_url}{separator}canva=connected", status_code=303)


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
