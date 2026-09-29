# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/videographer.py
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.services.videographer_service import videographer_service

router = APIRouter()


class ClipReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(..., min_length=3, max_length=1000)


class CanvaAutofillRequest(BaseModel):
    brand_template_id: str = Field(..., min_length=1, max_length=240)
    data: dict[str, Any]


@router.get("/assets", dependencies=[Depends(require_permission("video:read"))])
async def list_videographer_assets(
    owner_id: UUID | None = None,
    team: str | None = Query(None, min_length=2, max_length=80),
    audience: str | None = Query(None, min_length=2, max_length=80),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    assets = videographer_service.list_assets(db, owner_id=owner_id, team=team, audience=audience)
    return {"assets": [videographer_service.asset_payload(asset) for asset in assets]}


@router.post("/assets", dependencies=[Depends(require_permission("video:upload"))])
async def upload_videographer_video(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=3, max_length=240),
    team: str = Form("videographer", min_length=2, max_length=80),
    audience: str = Form("marketing", min_length=2, max_length=80),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    asset = await videographer_service.upload(db, current_user, file, title, team, audience)
    return videographer_service.asset_payload(asset)


@router.post("/assets/{asset_id}/transcribe", dependencies=[Depends(require_permission("video:edit"))])
async def transcribe_videographer_asset(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await videographer_service.transcribe(db, asset_id, current_user)


@router.post("/assets/{asset_id}/generate-clips", dependencies=[Depends(require_permission("video:edit"))])
async def generate_videographer_clips(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await videographer_service.generate_clips(db, asset_id, current_user)


@router.get("/assets/{asset_id}/outputs", dependencies=[Depends(require_permission("video:read"))])
async def get_videographer_outputs(asset_id: UUID, db: Session = Depends(get_db)):
    asset = videographer_service.get_asset(db, asset_id)
    return {"asset_id": str(asset.id), "outputs": asset.generated_outputs or []}


@router.post("/assets/{asset_id}/outputs/{output_index}/review", dependencies=[Depends(require_permission("video:approve"))])
async def review_videographer_output(
    asset_id: UUID,
    output_index: int,
    request: ClipReviewRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    return videographer_service.review_output(db, asset_id, output_index, request.decision, request.note, current_user)


@router.get("/canva/status", dependencies=[Depends(require_permission("design:canva"))])
async def get_videographer_canva_status(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return videographer_service.canva_status(db, current_user.id)


@router.post("/assets/{asset_id}/outputs/{output_index}/canva", dependencies=[Depends(require_permission("video:edit")), Depends(require_permission("design:canva"))])
async def create_videographer_canva_design(
    asset_id: UUID,
    output_index: int,
    request: CanvaAutofillRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    return await videographer_service.create_canva_design(
        db, asset_id, output_index, request.brand_template_id, request.data, current_user
    )


@router.post("/assets/{asset_id}/outputs/{output_index}/canva/poll", dependencies=[Depends(require_permission("video:read")), Depends(require_permission("design:canva"))])
async def poll_videographer_canva_design(
    asset_id: UUID,
    output_index: int,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    return await videographer_service.poll_canva_design(db, asset_id, output_index, current_user)


@router.post("/assets/{asset_id}/outputs/{output_index}/publish", dependencies=[Depends(require_permission("video:publish"))])
async def publish_videographer_output(
    asset_id: UUID,
    output_index: int,
    channel: str = Query(..., min_length=2, max_length=40),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    allowed_channels = {"instagram", "facebook", "linkedin", "tiktok", "youtube"}
    normalized_channel = channel.strip().lower()
    if normalized_channel not in allowed_channels:
        raise HTTPException(status_code=422, detail=f"Channel must be one of: {', '.join(sorted(allowed_channels))}")
    return await videographer_service.publish_output(db, asset_id, output_index, normalized_channel, current_user)