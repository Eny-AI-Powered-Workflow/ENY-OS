# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/videographer.py
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.marketing_intelligence import MarketingIntelligenceEvent, MarketingVideoAsset
from app.services.claude_service import ClaudeService
from app.services.marketing_video_service import marketing_video_service

router = APIRouter()


def _video_asset_payload(asset: MarketingVideoAsset) -> dict[str, Any]:
    return {
        "id": str(asset.id),
        "title": asset.title,
        "original_filename": asset.original_filename,
        "mime_type": asset.mime_type,
        "size_bytes": asset.size_bytes,
        "status": asset.status,
        "transcript": asset.transcript,
        "duration_seconds": asset.duration_seconds,
        "transcript_segments": asset.transcript_segments,
        "transcript_provider": asset.transcript_provider,
        "generated_outputs": asset.generated_outputs,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


@router.get("/assets", dependencies=[Depends(require_permission("video:read"))])
async def list_videographer_assets(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    assets = db.query(MarketingVideoAsset).order_by(MarketingVideoAsset.created_at.desc()).limit(100).all()
    return {"assets": [_video_asset_payload(asset) for asset in assets]}


@router.post("/assets", dependencies=[Depends(require_permission("video:upload"))])
async def upload_videographer_video(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=3, max_length=240),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)
    storage_path = await marketing_video_service.store_upload(file, size_bytes)
    asset = MarketingVideoAsset(
        title=title.strip(),
        original_filename=file.filename or "video-asset",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        storage_path=storage_path,
        created_by=current_user.id,
    )
    db.add(asset)
    db.flush()
    db.add(MarketingIntelligenceEvent(
        entity_type="video_asset",
        entity_id=asset.id,
        actor_id=current_user.id,
        event_type="uploaded",
        details={"filename": asset.original_filename, "size_bytes": size_bytes, "storage": "private_supabase_storage"},
    ))
    db.commit()
    return _video_asset_payload(asset)


@router.post("/assets/{asset_id}/transcribe", dependencies=[Depends(require_permission("video:edit"))])
async def transcribe_videographer_asset(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset not found")
    if asset.transcript:
        return _video_asset_payload(asset)
    result = await marketing_video_service.transcribe(asset.storage_path, asset.original_filename, asset.mime_type, asset.size_bytes)
    if result["status"] != "transcribed":
        asset.status = "transcription_required"
        db.add(MarketingIntelligenceEvent(
            entity_type="video_asset",
            entity_id=asset.id,
            actor_id=current_user.id,
            event_type="transcription_unavailable",
            details={"status": result["status"], "message": result.get("message")},
        ))
        db.commit()
        return {**_video_asset_payload(asset), "transcription": result}

    asset.transcript = result["text"]
    asset.duration_seconds = int(result["duration"]) if result.get("duration") is not None else None
    asset.transcript_segments = result["segments"]
    asset.transcript_provider = result["provider"]
    asset.status = "transcribed"
    db.add(MarketingIntelligenceEvent(
        entity_type="video_asset",
        entity_id=asset.id,
        actor_id=current_user.id,
        event_type="transcribed",
        details={"provider": result["provider"], "duration_seconds": result.get("duration"), "segment_count": len(result["segments"])},
    ))
    db.commit()
    return _video_asset_payload(asset)


@router.post("/assets/{asset_id}/generate-clips", dependencies=[Depends(require_permission("video:edit"))])
async def generate_videographer_clips(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset not found")
    if not asset.transcript:
        raise HTTPException(status_code=409, detail="Transcribe the video before generating clips")

    prompt = (
        "Create a short-form video clip plan for ENY Consulting based only on the transcript. "
        "Return valid JSON with a 'clips' array. Each clip should include title, start_seconds, end_seconds, "
        "rationale, caption, and hook."
        f"\nTranscript:\n{asset.transcript[:60000]}"
    )
    response = await ClaudeService().invoke(prompt=prompt, role_context="marketing", max_tokens=4000, temperature=0.3)
    try:
        generated = json.loads(response)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Clip generation returned invalid JSON") from exc

    clips = generated.get("clips") if isinstance(generated, dict) else []
    if not isinstance(clips, list):
        raise HTTPException(status_code=502, detail="Clip generation payload was malformed")

    asset.generated_outputs = clips
    asset.status = "ready_for_review"
    db.add(MarketingIntelligenceEvent(
        entity_type="video_asset",
        entity_id=asset.id,
        actor_id=current_user.id,
        event_type="clips_generated",
        details={"clip_count": len(clips)},
    ))
    db.commit()
    return {"id": str(asset.id), "status": asset.status, "clips": clips}


@router.post("/assets/{asset_id}/approve", dependencies=[Depends(require_permission("video:approve"))])
async def approve_videographer_asset(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset not found")
    if asset.status == "approved":
        return {"id": str(asset.id), "status": asset.status, "message": "Asset already approved"}
    asset.status = "approved"
    db.add(MarketingIntelligenceEvent(
        entity_type="video_asset",
        entity_id=asset.id,
        actor_id=current_user.id,
        event_type="approved",
        details={"approver": str(current_user.id)},
    ))
    db.commit()
    return {"id": str(asset.id), "status": asset.status}


@router.post("/assets/{asset_id}/publish", dependencies=[Depends(require_permission("video:publish"))])
async def publish_videographer_asset(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Video asset not found")
    if asset.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved video assets can be published")
    asset.status = "published"
    db.add(MarketingIntelligenceEvent(
        entity_type="video_asset",
        entity_id=asset.id,
        actor_id=current_user.id,
        event_type="published",
        details={"publisher": str(current_user.id)},
    ))
    db.commit()
    return {"id": str(asset.id), "status": asset.status}