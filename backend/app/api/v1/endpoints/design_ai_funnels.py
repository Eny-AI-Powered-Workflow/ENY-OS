# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/design_ai_funnels.py

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.design_system import (
    CanvaConnection,
    CanvaOAuthState,
    DesignAiDraft,
    DesignAsset,
    DesignAssetEvent,
    DesignAssetFile,
    DesignFunnel,
    DesignFunnelEvent,
    DesignFunnelVariant,
    DesignProviderEvent,
    DesignRequest,
    DesignSystemDocument,
    DesignTemplate,
)
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.services.canva_service import CanvaService, canva_service
from app.services.claude_service import ClaudeService
from app.services.design_asset_service import design_asset_service
from app.services.knowledge_service import retrieve_knowledge
from app.services.webflow_service import webflow_service

router = APIRouter()


class FunnelCreate(BaseModel):
    funnel_key: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9][a-z0-9._-]+$")
    title: str = Field(..., min_length=3, max_length=240)
    owner_id: Optional[UUID] = None
    conversion_events: list[str] = Field(..., min_length=1, max_length=30)
    page_id: Optional[str] = Field(None, max_length=240)


class FunnelVariantCreate(BaseModel):
    variant_key: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9._-]+$")
    title: str = Field(..., min_length=3, max_length=240)
    content_json: dict[str, Any]
    form_fields: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    conversion_event: str = Field(..., min_length=2, max_length=160)


class FunnelReview(BaseModel):
    note: str = Field(..., min_length=5, max_length=2000)


class DesignConceptRequest(BaseModel):
    max_concepts: int = Field(3, ge=1, le=5)


class CanvaAutofillRequest(BaseModel):
    template_id: UUID
    data: dict[str, dict[str, Any]]
    title: str = Field(..., min_length=1, max_length=255)


class CanvaExportRequest(BaseModel):
    format: Literal["png", "pdf"] = "png"


def _has_scope(db: Session, user_id: UUID, scope: str) -> bool:
    return db.query(Permission.id).join(RolePermission, Permission.id == RolePermission.permission_id).join(
        UserRole, RolePermission.role_id == UserRole.role_id
    ).filter(UserRole.user_id == user_id, Permission.scope == scope).first() is not None


def _provider_event(db: Session, provider: str, entity_type: str, entity_id: Optional[UUID], actor_id: UUID, event_type: str, status: str, details: dict[str, Any] | None = None) -> None:
    db.add(DesignProviderEvent(provider=provider, entity_type=entity_type, entity_id=entity_id, actor_id=actor_id, event_type=event_type, status=status, details=details or {}))


def _template_for_canva(db: Session, template_id: UUID, user_id: UUID) -> DesignTemplate:
    template = db.query(DesignTemplate).filter(DesignTemplate.id == template_id).first()
    if not template or template.status != "approved":
        raise HTTPException(status_code=404, detail="Approved Canva template not found")
    brand = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == template.base_brand_document_id).first()
    if not brand or brand.status != "approved" or brand.source_status != "verified" or brand.version != template.base_brand_version:
        raise HTTPException(status_code=409, detail="Template is not bound to the current approved brand-system version")
    if not _has_scope(db, user_id, "design:manage"):
        allowed = template.audience == "marketing" and _has_scope(db, user_id, "design:templates")
        allowed = allowed or template.audience in {"programs", "student_success"} and _has_scope(db, user_id, "design:read_programs")
        if not allowed:
            raise HTTPException(status_code=403, detail="This role cannot use the selected template audience")
    if template.provider != "manual_canva" or not template.provider_template_id:
        raise HTTPException(status_code=409, detail="Template has no Canva Brand Template ID")
    return template


def _require_canva_scopes(db: Session, user_id: UUID, required: set[str]) -> CanvaConnection:
    connection = db.query(CanvaConnection).filter(CanvaConnection.user_id == user_id, CanvaConnection.status == "connected").first()
    if not connection:
        raise HTTPException(status_code=409, detail="Connect Canva for this user first")
    missing = required - set(connection.scopes or [])
    if missing:
        raise HTTPException(status_code=403, detail=f"Reconnect Canva with the required scopes: {', '.join(sorted(missing))}")
    return connection


def _require_owned_request(db: Session, request_id: UUID, user_id: UUID) -> DesignRequest:
    request_row = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not request_row:
        raise HTTPException(status_code=404, detail="Design request not found")
    if request_row.requester_id != user_id and request_row.owner_id != user_id and not _has_scope(db, user_id, "design:manage"):
        raise HTTPException(status_code=403, detail="You cannot use this design request")
    if request_row.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Closed design requests cannot create new variants")
    return request_row


@router.get("/canva/status", dependencies=[Depends(require_permission("design:canva"))])
async def get_canva_connection_status(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return canva_service.connection_status(db, current_user.id)


@router.post("/canva/connect", dependencies=[Depends(require_permission("design:canva"))])
async def start_canva_connection(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    authorization_url = canva_service.authorization_url(db, current_user.id)
    _provider_event(db, "canva", "oauth", None, current_user.id, "authorization_started", "pending", {})
    db.commit()
    return {"authorization_url": authorization_url, "status": "authorization_required"}


@router.get("/canva/oauth/callback")
async def complete_canva_connection(code: str = Query(..., min_length=8), state: str = Query(..., min_length=16), db: Session = Depends(get_db)):
    user_id = await canva_service.complete_authorization(db, code, state)
    _provider_event(db, "canva", "oauth", None, user_id, "connected", "success", {})
    db.commit()
    redirect_url = settings.CANVA_POST_CONNECT_REDIRECT
    separator = "&" if "?" in redirect_url else "?"
    return RedirectResponse(url=f"{redirect_url}{separator}canva=connected", status_code=303)


@router.post("/canva/disconnect", dependencies=[Depends(require_permission("design:canva"))])
async def disconnect_canva(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    await canva_service.revoke(db, current_user.id)
    _provider_event(db, "canva", "oauth", None, current_user.id, "disconnected", "success", {})
    db.commit()
    return {"status": "disconnected"}


@router.post("/templates/{template_id}/canva-dataset", dependencies=[Depends(require_permission("design:canva"))])
async def refresh_canva_template_dataset(template_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    template = _template_for_canva(db, template_id, current_user.id)
    _require_canva_scopes(db, current_user.id, {"brandtemplate:content:read"})
    try:
        dataset = await canva_service.get_brand_template_dataset(db, current_user.id, template.provider_template_id)
        template.canva_dataset = dataset
        _provider_event(db, "canva", "design_template", template.id, current_user.id, "dataset_refreshed", "success", {"field_count": len(dataset), "template_version": template.version})
        db.commit()
    except HTTPException as exc:
        _provider_event(db, "canva", "design_template", template.id, current_user.id, "dataset_refresh_failed", "error", {"status_code": exc.status_code})
        db.commit()
        raise
    return {"template_id": str(template.id), "template_version": template.version, "dataset": dataset, "status": "connected"}


@router.get("/requests/{request_id}/ai-drafts", dependencies=[Depends(require_permission("design:ai"))])
async def list_design_ai_drafts(request_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    _require_owned_request(db, request_id, current_user.id)
    drafts = db.query(DesignAiDraft).filter(DesignAiDraft.request_id == request_id).order_by(DesignAiDraft.created_at.desc()).limit(50).all()
    return {"drafts": [{"id": str(draft.id), "title": draft.title, "visual_direction": draft.visual_direction, "copy_variants": draft.copy_variants, "template_suggestions": draft.template_suggestions, "source_documents": draft.source_documents, "status": draft.status, "created_at": draft.created_at.isoformat() if draft.created_at else None} for draft in drafts]}


@router.post("/requests/{request_id}/generate-concepts", dependencies=[Depends(require_permission("design:ai"))])
async def generate_design_concepts(request_id: UUID, request: DesignConceptRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    design_request = _require_owned_request(db, request_id, current_user.id)
    if design_request.audience not in {"marketing", "programs", "student_success"}:
        raise HTTPException(status_code=422, detail="AI design concepts require an explicit Marketing or Programs audience")
    if re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|(?:\+?\d[\d ()-]{7,}\d)", design_request.brief):
        raise HTTPException(status_code=422, detail="Remove personal email addresses and phone numbers before requesting AI design assistance")

    audience = design_request.audience
    retrieval_roles = ["marketing"] if audience == "marketing" else ["programs_manager", "customer_success"] if audience == "student_success" else ["programs_manager"]
    knowledge = await retrieve_knowledge(db, retrieval_roles, f"{design_request.title} {design_request.brief}", limit=8)
    approved_docs = db.query(DesignSystemDocument).filter(
        DesignSystemDocument.status == "approved",
        DesignSystemDocument.source_status == "verified",
        DesignSystemDocument.audience.in_([audience, "shared"]),
    ).order_by(DesignSystemDocument.updated_at.desc()).limit(20).all()
    templates = db.query(DesignTemplate).filter(
        DesignTemplate.audience.in_([audience, "shared"]),
        DesignTemplate.status == "approved",
    ).order_by(DesignTemplate.updated_at.desc()).limit(30).all()
    current_templates = []
    for template in templates:
        brand = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == template.base_brand_document_id).first()
        if brand and brand.status == "approved" and brand.source_status == "verified" and brand.version == template.base_brand_version:
            current_templates.append(template)
    template_context = [{"template_key": item.template_key, "title": item.title, "category": item.category, "locked_fields": item.locked_fields or [], "editable_fields": item.editable_fields or [], "brand_version": item.base_brand_version} for item in current_templates]
    knowledge_context = [{"title": item.title, "source": item.source_reference, "category": item.category, "content": item.content[:5000]} for item in approved_docs]
    source_documents = [{"title": item.get("title"), "source": item.get("source"), "type": "department_knowledge"} for item in knowledge]
    source_documents.extend({"title": item.title, "source": item.source_reference, "type": "approved_design_system", "version": item.version} for item in approved_docs)
    prompt = f"""Create {request.max_concepts} design concepts for this ENY request. Return JSON only with a concepts array; each concept must include title, visual_direction, copy_variants (array of objects with platform, headline, body, cta), template_suggestions (array of objects with template_key and rationale), and accessibility_notes.
Only use facts, offers, claims, colors, and visual rules present in the approved knowledge. Do not invent statistics, prices, results, or visual brand tokens. Suggest only templates from the allowed list and never suggest changing locked fields. Keep all output as a draft for Designer review. Do not create, export, publish, or call providers.
Request title: {design_request.title}
Audience: {audience}
Request type: {design_request.request_type}
Brief: {design_request.brief}
Approved department knowledge: {json.dumps(knowledge, default=str)}
Approved design foundation: {json.dumps(knowledge_context, default=str)}
Available current approved templates: {json.dumps(template_context, default=str)}""".replace("\n+", "\n")
    response = await ClaudeService().invoke(prompt=prompt, role_context=audience, max_tokens=3500, temperature=0.3)
    try:
        result = json.loads(response)
        concepts = result.get("concepts", []) if isinstance(result, dict) else []
    except json.JSONDecodeError as exc:
        _provider_event(db, "claude", "design_request", design_request.id, current_user.id, "concept_generation_failed", "error", {"reason": "invalid_json"})
        db.commit()
        raise HTTPException(status_code=502, detail="AI concept generation returned invalid structured output") from exc
    if not isinstance(concepts, list) or not concepts:
        raise HTTPException(status_code=502, detail="AI concept generation returned no concepts")
    template_lookup = {item.template_key: item for item in current_templates}
    created = []
    for concept in concepts[:request.max_concepts]:
        if not isinstance(concept, dict) or not concept.get("title") or not concept.get("visual_direction"):
            continue
        suggestions = []
        for suggestion in concept.get("template_suggestions", [])[:5]:
            if not isinstance(suggestion, dict):
                continue
            template = template_lookup.get(str(suggestion.get("template_key") or ""))
            if template:
                suggestions.append({"template_id": str(template.id), "template_key": template.template_key, "title": template.title, "rationale": str(suggestion.get("rationale") or "")[:1000], "template_version": template.version, "brand_version": template.base_brand_version})
        draft = DesignAiDraft(
            request_id=design_request.id,
            audience=audience,
            title=str(concept["title"])[:240],
            visual_direction=str(concept["visual_direction"])[:12000],
            copy_variants=concept.get("copy_variants", [])[:12] if isinstance(concept.get("copy_variants"), list) else [],
            template_suggestions=suggestions,
            source_documents=source_documents,
            prompt=prompt,
            created_by=current_user.id,
        )
        db.add(draft)
        db.flush()
        _provider_event(db, "claude", "design_ai_draft", draft.id, current_user.id, "concept_generated", "draft", {"request_id": str(design_request.id), "audience": audience, "source_count": len(source_documents)})
        created.append(draft)
    if not created:
        raise HTTPException(status_code=502, detail="AI output did not contain valid design concepts")
    db.commit()
    return {"status": "drafts_created", "drafts": [{"id": str(item.id), "title": item.title, "visual_direction": item.visual_direction, "copy_variants": item.copy_variants, "template_suggestions": item.template_suggestions, "source_documents": item.source_documents} for item in created]}


@router.post("/ai-drafts/{draft_id}/select", dependencies=[Depends(require_permission("design:ai"))])
async def select_design_ai_draft(draft_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    draft = db.query(DesignAiDraft).filter(DesignAiDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Design AI draft not found")
    _require_owned_request(db, draft.request_id, current_user.id)
    if draft.status not in {"draft", "selected"}:
        raise HTTPException(status_code=409, detail="Discarded AI design concept cannot be selected")
    draft.status = "selected"
    _provider_event(db, "claude", "design_ai_draft", draft.id, current_user.id, "selected_for_manual_review", "selected", {})
    db.commit()
    return {"id": str(draft.id), "status": draft.status}


@router.post("/ai-drafts/{draft_id}/autofill", dependencies=[Depends(require_permission("design:canva"))])
async def start_canva_autofill(draft_id: UUID, request: CanvaAutofillRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    draft = db.query(DesignAiDraft).filter(DesignAiDraft.id == draft_id).first()
    if not draft or draft.status != "selected":
        raise HTTPException(status_code=409, detail="Select an AI concept as a draft before requesting Canva Autofill")
    design_request = _require_owned_request(db, draft.request_id, current_user.id)
    _require_canva_scopes(db, current_user.id, {"brandtemplate:content:read", "design:content:write"})
    template = _template_for_canva(db, request.template_id, current_user.id)
    allowed_suggestions = {item.get("template_id") for item in (draft.template_suggestions or [])}
    if str(template.id) not in allowed_suggestions:
        raise HTTPException(status_code=422, detail="Choose a current approved template suggested for this AI draft")
    if template.audience != draft.audience and template.audience != "shared":
        raise HTTPException(status_code=403, detail="Template audience does not match the design request")
    dataset = template.canva_dataset or await canva_service.get_brand_template_dataset(db, current_user.id, template.provider_template_id)
    template.canva_dataset = dataset
    locked_fields = set(template.locked_fields or [])
    editable_fields = set(template.editable_fields or [])
    if set(request.data) - editable_fields or set(request.data) & locked_fields:
        raise HTTPException(status_code=422, detail="Canva data may only populate editable template fields; locked fields cannot be changed")
    for key, field_value in request.data.items():
        if key not in dataset or not isinstance(field_value, dict):
            raise HTTPException(status_code=422, detail=f"Canva field '{key}' is not part of the current template dataset")
        expected_type = dataset[key].get("type") if isinstance(dataset[key], dict) else None
        if expected_type != "text" or field_value.get("type") != "text" or not isinstance(field_value.get("text"), str):
            raise HTTPException(status_code=422, detail="Initial Canva Autofill supports only verified text fields; image/chart fields remain manual")
        if len(field_value["text"]) > 10000:
            raise HTTPException(status_code=422, detail="Canva text fields cannot exceed 10,000 characters")
    if not request.data:
        raise HTTPException(status_code=422, detail="Provide at least one approved editable Canva text field")
    if template.status != "approved" or template.base_brand_version != db.query(DesignSystemDocument).filter(DesignSystemDocument.id == template.base_brand_document_id).first().version:
        raise HTTPException(status_code=409, detail="Template or brand guidance is stale; refresh and approve a new template version")
    try:
        job = await canva_service.create_autofill(db, current_user.id, template.provider_template_id, request.title, request.data)
    except HTTPException as exc:
        _provider_event(db, "canva", "design_ai_draft", draft.id, current_user.id, "autofill_start_failed", "error", {"status_code": exc.status_code, "template_id": str(template.id)})
        db.commit()
        raise
    asset = DesignAsset(
        title=request.title,
        asset_type=template.category,
        audience=draft.audience,
        status="draft",
        provider="canva_autofill",
        request_id=design_request.id,
        template_id=template.id,
        template_version=template.version,
        locked_values_snapshot=template.locked_values or {},
        variant_values={key: value.get("text") for key, value in request.data.items()},
        brand_document_id=template.base_brand_document_id,
        brand_version=template.base_brand_version,
        campaign_name=design_request.campaign_name,
        program_name=design_request.program_name,
        source_content_id=design_request.source_content_id,
        source_video_asset_id=design_request.source_video_asset_id,
        generation_prompt=draft.prompt,
        generation_sources=draft.source_documents or [],
        generation_draft={"ai_draft_id": str(draft.id), "visual_direction": draft.visual_direction, "copy_variants": draft.copy_variants, "canva_data": request.data},
        canva_job_id=job["id"],
        usage_rights=template.usage_rights or {},
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(asset)
    db.flush()
    _provider_event(db, "canva", "design_asset", asset.id, current_user.id, "autofill_started", "in_progress", {"job_id": job["id"], "template_id": str(template.id), "template_version": template.version, "draft_id": str(draft.id)})
    db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="canva_autofill_started", details={"job_id": job["id"], "ai_draft_id": str(draft.id), "status": "draft"}))
    db.commit()
    return {"asset_id": str(asset.id), "job_id": job["id"], "status": "in_progress", "asset_status": "draft"}


@router.post("/assets/{asset_id}/canva/poll", dependencies=[Depends(require_permission("design:canva"))])
async def poll_canva_autofill(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id, DesignAsset.provider == "canva_autofill").first()
    if not asset or not asset.canva_job_id:
        raise HTTPException(status_code=404, detail="Canva Autofill asset or job not found")
    if asset.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the connected Canva user who started this job can poll it")
    _require_canva_scopes(db, current_user.id, {"design:meta:read"})
    job = await canva_service.get_autofill_job(db, current_user.id, asset.canva_job_id)
    if job.get("status") == "success":
        design = ((job.get("result") or {}).get("design") or {})
        asset.external_design_id = design.get("id")
        asset.external_design_url = design.get("url")
        urls = design.get("urls") or {}
        asset.external_edit_url = urls.get("edit_url")
        asset.external_view_url = urls.get("view_url")
        asset.external_thumbnail_url = (design.get("thumbnail") or {}).get("url")
        asset.external_urls_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        _provider_event(db, "canva", "design_asset", asset.id, current_user.id, "autofill_completed", "success", {"design_id": asset.external_design_id})
        db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="canva_autofill_completed", details={"design_id": asset.external_design_id, "internal_status": "draft"}))
    elif job.get("status") == "failed":
        failure = job.get("error") or {}
        _provider_event(db, "canva", "design_asset", asset.id, current_user.id, "autofill_failed", "error", {"error_code": failure.get("code"), "message": failure.get("message")})
        db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="canva_autofill_failed", details={"error": failure}))
    db.commit()
    return {"asset_id": str(asset.id), "job_id": job.get("id"), "job_status": job.get("status"), "asset_status": asset.status, "design": {"id": asset.external_design_id, "url": asset.external_design_url, "edit_url": asset.external_edit_url, "view_url": asset.external_view_url, "thumbnail_url": asset.external_thumbnail_url, "urls_expires_at": asset.external_urls_expires_at.isoformat() if asset.external_urls_expires_at else None}, "error": job.get("error")} 


@router.post("/assets/{asset_id}/canva/export", dependencies=[Depends(require_permission("design:canva"))])
async def start_canva_export(asset_id: UUID, request: CanvaExportRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id, DesignAsset.provider == "canva_autofill").first()
    if not asset or not asset.external_design_id:
        raise HTTPException(status_code=404, detail="Completed Canva design not found")
    if asset.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the Canva design owner can request an export")
    if asset.status != "approved":
        raise HTTPException(status_code=409, detail="Human approval is required before Canva export")
    _require_canva_scopes(db, current_user.id, {"design:content:read"})
    job = await canva_service.create_export(db, current_user.id, asset.external_design_id, request.format)
    asset.export_job_id = job["id"]
    db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="canva_export_started", details={"job_id": job["id"], "format": request.format, "status": asset.status}))
    _provider_event(db, "canva", "design_asset", asset.id, current_user.id, "export_started", "in_progress", {"job_id": job["id"], "format": request.format})
    db.commit()
    return {"asset_id": str(asset.id), "export_job_id": job["id"], "status": job.get("status", "in_progress")}


@router.post("/assets/{asset_id}/canva/export/poll", dependencies=[Depends(require_permission("design:canva"))])
async def poll_canva_export(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id, DesignAsset.provider == "canva_autofill").first()
    if not asset or not asset.export_job_id:
        raise HTTPException(status_code=404, detail="Canva export job not found")
    if asset.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the Canva design owner can poll its export")
    _require_canva_scopes(db, current_user.id, {"design:content:read"})
    job = await canva_service.get_export_job(db, current_user.id, asset.export_job_id)
    if job.get("status") == "success":
        urls = job.get("urls") or []
        if not urls:
            raise HTTPException(status_code=502, detail="Canva export completed without a download URL")
        file_bytes = await canva_service.download_export(urls[0])
        mime_type = "image/png" if urls[0].lower().split("?", 1)[0].endswith(".png") else "application/pdf"
        filename = f"{asset.title}.{'png' if mime_type == 'image/png' else 'pdf'}"
        path = await design_asset_service.upload_bytes(file_bytes, mime_type, asset.audience, filename)
        file_row = DesignAssetFile(asset_id=asset.id, file_kind="export", provider="canva", original_filename=filename, mime_type=mime_type, size_bytes=len(file_bytes), storage_path=path, created_by=current_user.id)
        db.add(file_row)
        db.flush()
        db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="canva_export_stored", details={"file_id": str(file_row.id), "filename": filename, "mime_type": mime_type, "bytes": len(file_bytes)}))
        _provider_event(db, "canva", "design_asset", asset.id, current_user.id, "export_completed", "success", {"file_id": str(file_row.id), "mime_type": mime_type})
    elif job.get("status") == "failed":
        _provider_event(db, "canva", "design_asset", asset.id, current_user.id, "export_failed", "error", {"error": job.get("error")})
        db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="canva_export_failed", details={"error": job.get("error")}))
    db.commit()
    return {"asset_id": str(asset.id), "job_status": job.get("status"), "error": job.get("error"), "file_count": db.query(DesignAssetFile.id).filter(DesignAssetFile.asset_id == asset.id).count()}


@router.get("/funnels/config", dependencies=[Depends(require_permission("design:funnels"))])
async def get_funnel_provider_config():
    return webflow_service.configuration_status()


@router.post("/funnels", dependencies=[Depends(require_permission("design:funnels"))])
async def create_design_funnel(request: FunnelCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    existing = db.query(DesignFunnel.id).filter(DesignFunnel.funnel_key == request.funnel_key).first()
    if existing:
        raise HTTPException(status_code=409, detail="Funnel key already exists")
    owner_id = request.owner_id or current_user.id
    if owner_id != current_user.id and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Only Designer owners and CEO can assign a different funnel owner")
    funnel = DesignFunnel(funnel_key=request.funnel_key, title=request.title, site_id=settings.WEBFLOW_SITE_ID or None, collection_id=settings.WEBFLOW_CMS_COLLECTION_ID or None, page_id=request.page_id, conversion_events=request.conversion_events, owner_id=owner_id, created_by=current_user.id)
    db.add(funnel)
    db.flush()
    db.add(DesignFunnelEvent(funnel_id=funnel.id, actor_id=current_user.id, event_type="created", details={"provider": "webflow", "conversion_events": request.conversion_events, "owner_id": str(owner_id)}))
    db.commit()
    return {"id": str(funnel.id), "funnel_key": funnel.funnel_key, "title": funnel.title, "provider": funnel.provider, "status": funnel.status}


def _funnel_payload(db: Session, funnel: DesignFunnel) -> dict[str, Any]:
    variants = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.funnel_id == funnel.id).order_by(DesignFunnelVariant.version.desc()).all()
    return {"id": str(funnel.id), "funnel_key": funnel.funnel_key, "title": funnel.title, "provider": funnel.provider, "site_id": funnel.site_id, "collection_id": funnel.collection_id, "page_id": funnel.page_id, "collection_item_id": funnel.collection_item_id, "public_url": funnel.public_url, "conversion_events": funnel.conversion_events or [], "status": funnel.status, "owner_id": str(funnel.owner_id), "variants": [{"id": str(item.id), "version": item.version, "variant_key": item.variant_key, "title": item.title, "content_json": item.content_json, "form_fields": item.form_fields, "conversion_event": item.conversion_event, "status": item.status, "external_item_id": item.external_item_id, "created_at": item.created_at.isoformat() if item.created_at else None} for item in variants], "updated_at": funnel.updated_at.isoformat() if funnel.updated_at else None}


@router.get("/funnels", dependencies=[Depends(require_permission("design:funnels"))])
async def list_design_funnels(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnels = db.query(DesignFunnel).order_by(DesignFunnel.updated_at.desc()).limit(200).all()
    return {"funnels": [_funnel_payload(db, funnel) for funnel in funnels]}


@router.post("/funnels/{funnel_id}/variants", dependencies=[Depends(require_permission("design:funnels"))])
async def create_funnel_variant(funnel_id: UUID, request: FunnelVariantCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    if funnel.owner_id != current_user.id and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Only the funnel owner or Designer/CEO can add variants")
    if request.conversion_event not in (funnel.conversion_events or []):
        raise HTTPException(status_code=422, detail="Variant conversion event must be registered on the funnel")
    if not isinstance(request.content_json.get("name"), str) or not isinstance(request.content_json.get("slug"), str):
        raise HTTPException(status_code=422, detail="Webflow fieldData requires name and slug")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", request.content_json["slug"]):
        raise HTTPException(status_code=422, detail="Funnel slug may contain lowercase letters, digits, and single hyphens")
    if len(json.dumps(request.content_json, ensure_ascii=True)) > 80000:
        raise HTTPException(status_code=413, detail="Funnel variant payload exceeds the 80 KB limit")
    if any(not field.get("name") or field.get("type") not in {"email", "text", "tel", "select", "checkbox"} for field in request.form_fields):
        raise HTTPException(status_code=422, detail="Form field definitions require a name and supported field type; do not store submitted lead data here")
    latest_version = db.query(DesignFunnelVariant.version).filter(DesignFunnelVariant.funnel_id == funnel.id).order_by(DesignFunnelVariant.version.desc()).first()
    version = (latest_version[0] if latest_version else 0) + 1
    variant = DesignFunnelVariant(funnel_id=funnel.id, version=version, variant_key=request.variant_key, title=request.title, content_json=request.content_json, form_fields=request.form_fields, conversion_event=request.conversion_event, created_by=current_user.id)
    db.add(variant)
    db.flush()
    db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=variant.id, actor_id=current_user.id, event_type="variant_created", details={"version": version, "variant_key": variant.variant_key, "conversion_event": variant.conversion_event}))
    db.commit()
    return {"id": str(variant.id), "version": variant.version, "status": variant.status}


@router.post("/funnels/{funnel_id}/variants/{variant_id}/submit", dependencies=[Depends(require_permission("design:funnels"))])
async def submit_funnel_variant(funnel_id: UUID, variant_id: UUID, note: str = Query(..., min_length=3, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    variant = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.id == variant_id, DesignFunnelVariant.funnel_id == funnel_id).first()
    if not funnel or not variant:
        raise HTTPException(status_code=404, detail="Funnel or variant not found")
    if variant.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft funnel variants can be submitted")
    variant.status = "in_review"
    funnel.status = "in_review"
    db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=variant.id, actor_id=current_user.id, event_type="variant_submitted", details={"note": note, "version": variant.version}))
    db.commit()
    return {"id": str(variant.id), "status": variant.status}


@router.post("/funnels/{funnel_id}/variants/{variant_id}/approve", dependencies=[Depends(require_permission("design:review_marketing"))])
async def approve_funnel_variant(funnel_id: UUID, variant_id: UUID, request: FunnelReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    variant = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.id == variant_id, DesignFunnelVariant.funnel_id == funnel_id).first()
    if not funnel or not variant:
        raise HTTPException(status_code=404, detail="Funnel or variant not found")
    if variant.status != "in_review":
        raise HTTPException(status_code=409, detail="Only in-review funnel variants can be approved")
    variant.status = "approved"
    variant.approved_by = current_user.id
    variant.approved_at = datetime.now(timezone.utc)
    funnel.status = "approved"
    funnel.approved_by = current_user.id
    funnel.approved_at = variant.approved_at
    db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=variant.id, actor_id=current_user.id, event_type="variant_approved", details={"note": request.note, "version": variant.version}))
    db.commit()
    return {"id": str(variant.id), "status": variant.status, "approved_at": variant.approved_at.isoformat()}


@router.post("/funnels/{funnel_id}/variants/{variant_id}/publish", dependencies=[Depends(require_permission("design:publish_marketing"))])
async def publish_funnel_variant(funnel_id: UUID, variant_id: UUID, request: FunnelReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    variant = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.id == variant_id, DesignFunnelVariant.funnel_id == funnel_id).first()
    if not funnel or not variant:
        raise HTTPException(status_code=404, detail="Funnel or variant not found")
    if variant.status != "approved":
        raise HTTPException(status_code=409, detail="Marketing Lead/CEO approval is required before funnel publishing")
    if not (funnel.collection_id or settings.WEBFLOW_CMS_COLLECTION_ID) or not settings.WEBFLOW_ACCESS_TOKEN:
        raise HTTPException(status_code=503, detail="Configure WEBFLOW_ACCESS_TOKEN and WEBFLOW_CMS_COLLECTION_ID before publishing")
    latest_published = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.funnel_id == funnel.id, DesignFunnelVariant.status == "published").order_by(DesignFunnelVariant.version.desc()).first()
    prior_content = latest_published.content_json if latest_published else {}
    prior_item_id = funnel.collection_item_id
    funnel.collection_item_id = prior_item_id
    _provider_event(db, "webflow", "funnel_variant", variant.id, current_user.id, "publish_started", "in_progress", {"funnel_id": str(funnel.id), "version": variant.version, "note": request.note})
    db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=variant.id, actor_id=current_user.id, event_type="publish_started", details={"version": variant.version, "previous_item_id": prior_item_id, "note": request.note}))
    db.commit()
    try:
        staged = await webflow_service.stage_variant(funnel, variant)
        item_id = staged["item_id"]
        variant.external_item_id = item_id
        funnel.collection_item_id = item_id
        db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=variant.id, actor_id=current_user.id, event_type="webflow_staged", details={"item_id": item_id, "provider_response": staged.get("provider_response")}))
        db.commit()
        published = await webflow_service.publish_variant(funnel, item_id)
    except HTTPException as exc:
        _provider_event(db, "webflow", "funnel_variant", variant.id, current_user.id, "publish_failed", "error", {"status_code": exc.status_code, "detail": str(exc.detail)})
        db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=variant.id, actor_id=current_user.id, event_type="publish_failed", details={"status_code": exc.status_code, "detail": str(exc.detail)}))
        db.commit()
        raise
    variant.previous_published_snapshot = prior_content
    if latest_published:
        latest_published.status = "superseded"
    variant.status = "published"
    variant.published_by = current_user.id
    variant.published_at = datetime.now(timezone.utc)
    funnel.status = "published"
    funnel.published_by = current_user.id
    funnel.published_at = variant.published_at
    slug = str((variant.content_json or {}).get("slug") or "").strip("/")
    funnel.public_url = f"{settings.WEBFLOW_PUBLIC_BASE_URL.rstrip('/')}/{slug}" if settings.WEBFLOW_PUBLIC_BASE_URL and slug else funnel.public_url
    db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=variant.id, actor_id=current_user.id, event_type="published", details={"item_id": item_id, "version": variant.version, "provider_status": published["status"], "rollback_available": bool(prior_content)}))
    _provider_event(db, "webflow", "funnel_variant", variant.id, current_user.id, "published", "success", {"funnel_id": str(funnel.id), "item_id": item_id, "version": variant.version})
    db.commit()
    return {"funnel_id": str(funnel.id), "variant_id": str(variant.id), "status": variant.status, "provider": "webflow", "external_item_id": item_id, "public_url": funnel.public_url, "rollback_available": bool(prior_content)}


@router.post("/funnels/{funnel_id}/variants/{source_variant_id}/rollback", dependencies=[Depends(require_permission("design:funnels"))])
async def create_funnel_rollback(funnel_id: UUID, source_variant_id: UUID, note: str = Query(..., min_length=5, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    source = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.id == source_variant_id, DesignFunnelVariant.funnel_id == funnel_id).first()
    if not funnel or not source or source.status not in {"published", "superseded"}:
        raise HTTPException(status_code=404, detail="Published rollback source variant not found")
    if funnel.owner_id != current_user.id and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Only the funnel owner or Designer/CEO can create a rollback")
    latest_version = db.query(DesignFunnelVariant.version).filter(DesignFunnelVariant.funnel_id == funnel.id).order_by(DesignFunnelVariant.version.desc()).first()
    version = (latest_version[0] if latest_version else 0) + 1
    rollback = DesignFunnelVariant(funnel_id=funnel.id, version=version, variant_key=f"rollback-v{source.version}", title=f"Rollback: {source.title}", content_json=source.content_json, form_fields=source.form_fields, conversion_event=source.conversion_event, external_item_id=funnel.collection_item_id, created_by=current_user.id)
    db.add(rollback)
    db.flush()
    db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=rollback.id, actor_id=current_user.id, event_type="rollback_created", details={"source_variant_id": str(source.id), "source_version": source.version, "version": version, "note": note}))
    db.commit()
    return {"id": str(rollback.id), "version": rollback.version, "status": rollback.status, "source_variant_id": str(source.id), "next_step": "submit for review"}


@router.get("/funnels/{funnel_id}/history", dependencies=[Depends(require_permission("design:funnels"))])
async def get_funnel_history(funnel_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    events = db.query(DesignFunnelEvent).filter(DesignFunnelEvent.funnel_id == funnel.id).order_by(DesignFunnelEvent.created_at.desc()).limit(500).all()
    return {"events": [{"variant_id": str(item.variant_id) if item.variant_id else None, "event_type": item.event_type, "details": item.details, "actor_id": str(item.actor_id), "created_at": item.created_at.isoformat() if item.created_at else None} for item in events]}
