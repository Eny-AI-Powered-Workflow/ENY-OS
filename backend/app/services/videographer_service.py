# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/videographer_service.py
import json
import math
from typing import Any
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.marketing_intelligence import MarketingIntelligenceEvent, MarketingVideoAsset
from app.services.canva_service import canva_service
from app.services.claude_service import ClaudeService
from app.services.marketing_video_service import marketing_video_service
from app.services.n8n_service import N8NService


class VideographerService:
    """Coordinate video storage, AI providers, Canva, and n8n behind the API boundary."""

    def canva_status(self, db: Session, user_id: UUID) -> dict[str, Any]:
        """Read the requesting user's Canva connection through the Canva provider service."""
        return canva_service.connection_status(db, user_id)

    @staticmethod
    def asset_payload(asset: MarketingVideoAsset) -> dict[str, Any]:
        return {
            "id": str(asset.id),
            "title": asset.title,
            "original_filename": asset.original_filename,
            "mime_type": asset.mime_type,
            "size_bytes": asset.size_bytes,
            "status": asset.status,
            "team": asset.team,
            "audience": asset.audience,
            "owner_id": str(asset.created_by),
            "transcript": asset.transcript,
            "duration_seconds": asset.duration_seconds,
            "transcript_segments": asset.transcript_segments,
            "transcript_provider": asset.transcript_provider,
            "generated_outputs": asset.generated_outputs or [],
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        }

    @staticmethod
    def get_asset(db: Session, asset_id: UUID) -> MarketingVideoAsset:
        asset = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Video asset not found")
        return asset

    def list_assets(
        self,
        db: Session,
        *,
        owner_id: UUID | None = None,
        team: str | None = None,
        audience: str | None = None,
    ) -> list[MarketingVideoAsset]:
        query = db.query(MarketingVideoAsset)
        if owner_id:
            query = query.filter(MarketingVideoAsset.created_by == owner_id)
        if team:
            query = query.filter(MarketingVideoAsset.team == team)
        if audience:
            query = query.filter(MarketingVideoAsset.audience == audience)
        return query.order_by(MarketingVideoAsset.created_at.desc()).limit(100).all()

    async def upload(
        self,
        db: Session,
        current_user: Any,
        upload: UploadFile,
        title: str,
        team: str,
        audience: str,
    ) -> MarketingVideoAsset:
        upload.file.seek(0, 2)
        size_bytes = upload.file.tell()
        upload.file.seek(0)
        storage_path = await marketing_video_service.store_upload(upload, size_bytes)
        asset = MarketingVideoAsset(
            title=title.strip(),
            original_filename=upload.filename or "video-asset",
            mime_type=upload.content_type or "application/octet-stream",
            size_bytes=size_bytes,
            storage_path=storage_path,
            team=team,
            audience=audience,
            created_by=current_user.id,
        )
        db.add(asset)
        db.flush()
        self._event(db, asset, current_user.id, "uploaded", {
            "filename": asset.original_filename,
            "size_bytes": size_bytes,
            "storage": "private_supabase_storage",
        })
        db.commit()
        return asset

    async def transcribe(self, db: Session, asset_id: UUID, current_user: Any) -> dict[str, Any]:
        asset = self.get_asset(db, asset_id)
        if asset.transcript:
            return {**self.asset_payload(asset), "transcription": {"status": "already_transcribed"}}

        result = await marketing_video_service.transcribe(
            asset.storage_path, asset.original_filename, asset.mime_type, asset.size_bytes
        )
        if result["status"] != "transcribed":
            asset.status = "transcription_required"
            self._event(db, asset, current_user.id, "transcription_unavailable", {
                "status": result["status"], "message": result.get("message"),
            })
            db.commit()
            return {**self.asset_payload(asset), "transcription": result}

        asset.transcript = result["text"]
        asset.duration_seconds = int(result["duration"]) if result.get("duration") is not None else None
        asset.transcript_segments = result["segments"]
        asset.transcript_provider = result["provider"]
        asset.status = "transcribed"
        self._event(db, asset, current_user.id, "transcribed", {
            "provider": result["provider"],
            "duration_seconds": result.get("duration"),
            "segment_count": len(result["segments"]),
        })
        db.commit()
        return self.asset_payload(asset)

    async def generate_clips(self, db: Session, asset_id: UUID, current_user: Any) -> dict[str, Any]:
        asset = self.get_asset(db, asset_id)
        if not asset.transcript:
            raise HTTPException(status_code=409, detail="Transcribe the video before generating clips")

        prompt = f"""Create up to five short-form clip recommendations for ENY Consulting using only this transcript.
Return valid JSON only: {{"clips":[{{"title":"", "start_seconds":0, "end_seconds":30, "rationale":"", "caption":"", "hook":""}}]}}.
Every timestamp must fall within the source duration ({asset.duration_seconds or 0} seconds). Do not invent claims, statistics, offers, or facts.
Transcript segments: {json.dumps((asset.transcript_segments or [])[:500], default=str)}
Transcript: {asset.transcript[:60000]}"""
        response = await ClaudeService().invoke(
            prompt=prompt, role_context="marketing", max_tokens=4000, temperature=0.2
        )
        try:
            generated = json.loads(response)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="Clip generation returned invalid JSON") from exc
        raw_clips = generated.get("clips") if isinstance(generated, dict) else None
        if not isinstance(raw_clips, list):
            raise HTTPException(status_code=502, detail="Clip generation payload was malformed")

        clips = []
        for clip in raw_clips[:5]:
            normalized = self._normalize_clip(clip, asset.duration_seconds)
            if normalized:
                clips.append(normalized)
        if not clips:
            raise HTTPException(status_code=502, detail="Clip generation returned no valid timestamped clips")

        asset.generated_outputs = clips
        asset.status = "ready_for_review"
        self._event(db, asset, current_user.id, "clips_generated", {"clip_count": len(clips), "provider": "Claude"})
        db.commit()
        return {"id": str(asset.id), "status": asset.status, "clips": clips}

    def review_output(
        self,
        db: Session,
        asset_id: UUID,
        output_index: int,
        decision: str,
        note: str,
        current_user: Any,
    ) -> dict[str, Any]:
        asset = self.get_asset(db, asset_id)
        outputs = list(asset.generated_outputs or [])
        if output_index < 0 or output_index >= len(outputs):
            raise HTTPException(status_code=404, detail="Generated clip not found")
        if decision not in {"approved", "rejected"}:
            raise HTTPException(status_code=422, detail="Decision must be approved or rejected")
        output = dict(outputs[output_index])
        output.update({"status": decision, "review_note": note.strip(), "reviewed_by": str(current_user.id)})
        outputs[output_index] = output
        asset.generated_outputs = outputs
        asset.status = "approved" if decision == "approved" else "ready_for_review"
        self._event(db, asset, current_user.id, f"clip_{decision}", {
            "output_index": output_index, "title": output.get("title"), "note": note.strip(),
        })
        db.commit()
        return {"id": str(asset.id), "status": asset.status, "clip": output}

    async def create_canva_design(
        self,
        db: Session,
        asset_id: UUID,
        output_index: int,
        brand_template_id: str,
        data: dict[str, Any],
        current_user: Any,
    ) -> dict[str, Any]:
        asset = self.get_asset(db, asset_id)
        outputs = list(asset.generated_outputs or [])
        if output_index < 0 or output_index >= len(outputs):
            raise HTTPException(status_code=404, detail="Generated clip not found")
        output = dict(outputs[output_index])
        if output.get("status") != "approved":
            raise HTTPException(status_code=409, detail="Approve the clip before creating its Canva design")
        dataset = await canva_service.get_brand_template_dataset(db, current_user.id, brand_template_id)
        allowed_fields = set(dataset)
        if not data or set(data) - allowed_fields:
            raise HTTPException(status_code=422, detail="Canva data must use fields from the selected approved template")
        job = await canva_service.create_autofill(
            db, current_user.id, brand_template_id, str(output.get("title") or asset.title), data
        )
        output["canva"] = {"job_id": job["id"], "status": job.get("status") or "in_progress"}
        outputs[output_index] = output
        asset.generated_outputs = outputs
        self._event(db, asset, current_user.id, "canva_autofill_started", {
            "output_index": output_index, "job_id": job["id"],
        })
        db.commit()
        return {"id": str(asset.id), "clip": output, "canva_job": job}

    async def poll_canva_design(
        self,
        db: Session,
        asset_id: UUID,
        output_index: int,
        current_user: Any,
    ) -> dict[str, Any]:
        asset = self.get_asset(db, asset_id)
        outputs = list(asset.generated_outputs or [])
        if output_index < 0 or output_index >= len(outputs):
            raise HTTPException(status_code=404, detail="Generated clip not found")
        output = dict(outputs[output_index])
        canva_state = output.get("canva") or {}
        job_id = canva_state.get("job_id")
        if not job_id:
            raise HTTPException(status_code=404, detail="Canva Autofill job not found")

        job = await canva_service.get_autofill_job(db, current_user.id, job_id)
        updated_canva = {"job_id": job_id, "status": job.get("status") or "in_progress"}
        if job.get("status") == "success":
            design = ((job.get("result") or {}).get("design") or {})
            urls = design.get("urls") or {}
            updated_canva.update({
                "design_id": design.get("id"),
                "url": design.get("url"),
                "edit_url": urls.get("edit_url"),
                "view_url": urls.get("view_url"),
                "thumbnail_url": (design.get("thumbnail") or {}).get("url"),
            })
        elif job.get("status") == "failed":
            updated_canva["error"] = job.get("error")
        output["canva"] = updated_canva
        outputs[output_index] = output
        asset.generated_outputs = outputs
        self._event(db, asset, current_user.id, "canva_autofill_polled", {
            "output_index": output_index, "job_id": job_id, "status": updated_canva["status"],
        })
        db.commit()
        return {"id": str(asset.id), "clip": output, "canva_job": job}

    async def publish_output(
        self,
        db: Session,
        asset_id: UUID,
        output_index: int,
        channel: str,
        current_user: Any,
    ) -> dict[str, Any]:
        asset = self.get_asset(db, asset_id)
        outputs = list(asset.generated_outputs or [])
        if output_index < 0 or output_index >= len(outputs):
            raise HTTPException(status_code=404, detail="Generated clip not found")
        output = dict(outputs[output_index])
        if output.get("status") != "approved":
            raise HTTPException(status_code=409, detail="Only approved clips can be published")
        media_url = await marketing_video_service.create_signed_url(asset.storage_path)
        result = await N8NService().trigger_workflow("eny-video-publish", {
            "asset_id": str(asset.id),
            "output_index": output_index,
            "title": output.get("title"),
            "caption": output.get("caption"),
            "hook": output.get("hook"),
            "source_media_url": media_url,
            "start_seconds": output["start_seconds"],
            "end_seconds": output["end_seconds"],
            "channel": channel,
            "approved_by": output.get("reviewed_by"),
            "requested_by": str(current_user.id),
        })
        if result.get("status") not in {"success", "published"} or not result.get("published"):
            raise HTTPException(
                status_code=502,
                detail=result.get("error") or result.get("message") or "The publishing workflow did not confirm publication",
            )
        output.update({"status": "published", "channel": channel, "published_url": result.get("url")})
        outputs[output_index] = output
        asset.generated_outputs = outputs
        asset.status = "published"
        self._event(db, asset, current_user.id, "clip_published", {
            "output_index": output_index, "channel": channel, "url": result.get("url"),
            "workflow": "eny-video-publish",
        })
        db.commit()
        return {"id": str(asset.id), "status": asset.status, "clip": output, "workflow": result}

    @staticmethod
    def _normalize_clip(clip: Any, duration_seconds: int | None) -> dict[str, Any] | None:
        if not isinstance(clip, dict):
            return None
        try:
            start = float(clip.get("start_seconds"))
            end = float(clip.get("end_seconds"))
        except (TypeError, ValueError):
            return None
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            return None
        if duration_seconds is not None and end > duration_seconds:
            return None
        return {
            "kind": "short_form_clip",
            "title": str(clip.get("title") or "Untitled clip")[:240],
            "start_seconds": start,
            "end_seconds": end,
            "rationale": str(clip.get("rationale") or "")[:2000],
            "caption": str(clip.get("caption") or "")[:5000],
            "hook": str(clip.get("hook") or "")[:1000],
            "status": "draft",
        }

    @staticmethod
    def _event(db: Session, asset: MarketingVideoAsset, actor_id: UUID, event_type: str, details: dict[str, Any]) -> None:
        db.add(MarketingIntelligenceEvent(
            entity_type="video_asset", entity_id=asset.id, actor_id=actor_id,
            event_type=event_type, details=details,
        ))


videographer_service = VideographerService()