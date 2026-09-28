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
    DesignFunnelExperiment,
    DesignFunnelMeasurement,
    DesignFunnelVariant,
    DesignProviderEvent,
    DesignRequest,
    DesignSystemDocument,
    DesignTemplate,
    ProgramMaterialInstance,
    ProgramMaterialTemplate,
)
from app.models.operational_alert import OperationalAlert
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


class FunnelMeasurementCreate(BaseModel):
    variant_id: Optional[UUID] = None
    event_type: Literal["visit", "form_start", "form_complete", "conversion", "attribution"] = "visit"
    conversion_event: Optional[str] = Field(None, min_length=2, max_length=160)
    source: str = Field(default="direct", min_length=1, max_length=80)
    provider: str = Field(default="webflow", min_length=1, max_length=80)
    campaign_name: Optional[str] = Field(None, max_length=160)
    session_key: Optional[str] = Field(None, max_length=200)
    referral_url: Optional[str] = Field(None, max_length=2000)
    details: dict[str, Any] = Field(default_factory=dict)


class FunnelExperimentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=180)
    goal_event: str = Field(..., min_length=2, max_length=160)
    hypothesis: str = Field(..., min_length=10, max_length=4000)
    control_variant_id: UUID
    treatment_variant_id: UUID
    traffic_split: int = Field(50, ge=5, le=95)
    notes: Optional[str] = Field(None, max_length=2000)


class ProgramMaterialTemplateCreate(BaseModel):
    template_key: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9][a-z0-9._-]+$")
    title: str = Field(..., min_length=3, max_length=240)
    category: str = Field(..., min_length=2, max_length=80)
    audience: Literal["programs", "student_success", "shared"]
    allowed_fields: list[str] = Field(..., min_length=1, max_length=50)
    required_fields: list[str] = Field(default_factory=list, max_length=20)
    template_json: dict[str, Any] = Field(default_factory=dict)
    usage_rights: dict[str, Any] = Field(default_factory=dict)


class ProgramMaterialRenderRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    allow_pii: bool = False


def _has_scope(db: Session, user_id: UUID, scope: str) -> bool:
    return db.query(Permission.id).join(RolePermission, Permission.id == RolePermission.permission_id).join(
        UserRole, RolePermission.role_id == UserRole.role_id
    ).filter(UserRole.user_id == user_id, Permission.scope == scope).first() is not None


def _provider_event(db: Session, provider: str, entity_type: str, entity_id: Optional[UUID], actor_id: UUID, event_type: str, status: str, details: dict[str, Any] | None = None) -> None:
    db.add(DesignProviderEvent(provider=provider, entity_type=entity_type, entity_id=entity_id, actor_id=actor_id, event_type=event_type, status=status, details=details or {}))


def _raise_design_alert(db: Session, alert_type: str, source: str, message: str, details: dict[str, Any], severity: str = "warning") -> None:
    existing = db.query(OperationalAlert).filter(
        OperationalAlert.team == "design",
        OperationalAlert.alert_type == alert_type,
        OperationalAlert.source == source,
        OperationalAlert.status == "open",
    ).first()
    if existing:
        existing.details = {**(existing.details or {}), **details}
        existing.message = message
        existing.severity = severity
        return
    db.add(OperationalAlert(team="design", alert_type=alert_type, severity=severity, source=source, message=message, details=details))


def _as_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _hours_between(start: Any, end: Any) -> Optional[float]:
    start_dt = _as_datetime(start)
    end_dt = _as_datetime(end)
    if start_dt is None or end_dt is None or end_dt < start_dt:
        return None
    return round((end_dt - start_dt).total_seconds() / 3600, 2)


def _summarize_design_operations_metrics(
    requests: list[Any],
    assets: list[Any],
    templates: list[Any],
    design_documents: list[Any],
    funnel_experiments: list[Any],
    measurements: list[Any],
    provider_events: list[Any],
    alerts: list[Any],
) -> dict[str, Any]:
    request_turnaround = [hours for request in requests if request.status == "completed" and (hours := _hours_between(request.created_at, request.updated_at)) is not None]
    asset_approval = [hours for asset in assets if asset.approved_at and (hours := _hours_between(asset.created_at, asset.approved_at)) is not None]
    template_reuse = [
        {"template_key": template.template_key, "title": getattr(template, "title", ""), "usage_count": int(getattr(template, "usage_count", 0) or 0)}
        for template in templates
    ]
    template_reuse.sort(key=lambda item: (-item["usage_count"], item["template_key"]))

    brand_review_outcomes: dict[str, dict[str, int]] = {}
    for document in design_documents:
        audience = getattr(document, "audience", "shared")
        bucket = brand_review_outcomes.setdefault(audience, {"approved": 0, "changes_requested": 0, "in_review": 0, "draft": 0, "total": 0})
        bucket[document.status] = bucket.get(document.status, 0) + 1
        bucket["total"] += 1

    failure_events = [
        event for event in provider_events
        if getattr(event, "status", "") == "error"
        and getattr(event, "provider", "") == "webflow"
        and "publish_failed" in str(getattr(event, "event_type", ""))
    ]

    experiment_results: dict[str, dict[str, Any]] = {}
    for experiment in funnel_experiments:
        goal = getattr(experiment, "goal_event", "unknown")
        entry = experiment_results.setdefault(goal, {"total": 0, "wins": 0, "winner_rate": 0})
        entry["total"] += 1
        if getattr(experiment, "winner_variant_id", None):
            entry["wins"] += 1
    for goal, entry in experiment_results.items():
        entry["winner_rate"] = round(entry["wins"] / entry["total"], 2) if entry["total"] else 0

    conversion_by_source: dict[str, int] = {}
    for measurement in measurements:
        if getattr(measurement, "event_type", None) != "conversion":
            continue
        source = getattr(measurement, "source", "direct") or "direct"
        value = int(getattr(measurement, "conversion_value", 0) or 0)
        conversion_by_source[source] = conversion_by_source.get(source, 0) + value

    open_alerts = [
        {
            "alert_type": alert.alert_type,
            "source": alert.source,
            "message": alert.message,
            "severity": alert.severity,
            "status": alert.status,
            "created_at": alert.created_at.isoformat() if getattr(alert, "created_at", None) else None,
        }
        for alert in alerts
        if getattr(alert, "status", None) == "open"
    ]

    return {
        "request_turnaround_hours": round(min(request_turnaround), 2) if request_turnaround else None,
        "asset_approval_hours": round(min(asset_approval), 2) if asset_approval else None,
        "template_reuse": template_reuse[:10],
        "brand_review_outcomes": brand_review_outcomes,
        "funnel_publishing_failures": len(failure_events),
        "experiment_results": experiment_results,
        "conversion_by_source": conversion_by_source,
        "open_alerts": open_alerts,
    }


def _design_operations_runbook() -> dict[str, Any]:
    return {
        "provider_setup": {
            "canva": "Connect Canva with brandtemplate:content:read and design:content:write scopes, and keep the connected user mapped to the correct design owner.",
            "webflow": "Set WEBFLOW_ACCESS_TOKEN and WEBFLOW_CMS_COLLECTION_ID before publishing. Confirm the public base URL matches the live site domain.",
            "tracking": "Verify GTM/GA4 event names and funnel conversion events match the exact names used in the funnel variant payload and measurement ingestion.",
        },
        "recovery_actions": {
            "failed_exports": "Re-run the Canva export job from the approved asset, verify asset approval status, and confirm the file has a valid output URL before publishing.",
            "funnel_publish_failures": "Check the Webflow collection item and token permissions, then re-stage and publish the last approved variant with a rollback snapshot in hand.",
            "form_breakage": "Review the latest form field definitions, confirm all required names/types match the funnel variant schema, and re-submit the variant for approval.",
            "tracking_outages": "Compare expected conversion events with live GTM/GA4 telemetry, validate the page snippet, and confirm the funnel variant slug and conversion_event names are aligned.",
        },
        "review_rituals": {
            "weekly": "Review open design alerts, approval backlog, template reuse, and approval SLA adherence once per week.",
            "launch": "Before publishing a new marketing or programs funnel, confirm the approved design system and a current marketing review approval are both in place.",
            "post_launch": "Compare experiment winner rate and source conversion totals against the previous 30-day baseline before broad rollout.",
        },
        "ownership": {
            "design_owner": "Graphic Designer manages production quality, template approvals, and Canva/Webflow handoff.",
            "marketing_review": "Marketing reviewer approves or rejects funnel and creative variants before publication.",
            "operations_owner": "Operations or the department lead monitors alerts, tracks failures, and ensures recovery steps are completed.",
        },
    }


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
        _raise_design_alert(db, "canva_export_failed", "canva", "Canva export failed for an approved design asset.", {"asset_id": str(asset.id), "error": job.get("error")}, "critical")
        db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="canva_export_failed", details={"error": job.get("error")}))
    db.commit()
    return {"asset_id": str(asset.id), "job_status": job.get("status"), "error": job.get("error"), "file_count": db.query(DesignAssetFile.id).filter(DesignAssetFile.asset_id == asset.id).count()}


@router.get("/operations/report", dependencies=[Depends(require_permission("design:analytics"))])
async def get_design_operations_report(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    window_start = datetime.now(timezone.utc) - timedelta(days=30)
    requests = db.query(DesignRequest).filter(DesignRequest.created_at >= window_start).order_by(DesignRequest.created_at.desc()).all()
    assets = db.query(DesignAsset).filter(DesignAsset.created_at >= window_start).order_by(DesignAsset.created_at.desc()).all()
    templates = db.query(ProgramMaterialTemplate).filter(ProgramMaterialTemplate.created_at >= window_start).order_by(ProgramMaterialTemplate.created_at.desc()).all()
    design_documents = db.query(DesignSystemDocument).filter(DesignSystemDocument.created_at >= window_start).order_by(DesignSystemDocument.created_at.desc()).all()
    funnel_experiments = db.query(DesignFunnelExperiment).filter(DesignFunnelExperiment.created_at >= window_start).order_by(DesignFunnelExperiment.created_at.desc()).all()
    measurements = db.query(DesignFunnelMeasurement).filter(DesignFunnelMeasurement.observed_at >= window_start).order_by(DesignFunnelMeasurement.observed_at.desc()).all()
    provider_events = db.query(DesignProviderEvent).filter(DesignProviderEvent.created_at >= window_start).order_by(DesignProviderEvent.created_at.desc()).all()
    alerts = db.query(OperationalAlert).filter(OperationalAlert.team == "design", OperationalAlert.created_at >= window_start).order_by(OperationalAlert.created_at.desc()).all()
    report = _summarize_design_operations_metrics(requests, assets, templates, design_documents, funnel_experiments, measurements, provider_events, alerts)
    report["runbook"] = _design_operations_runbook()
    report["period_start"] = window_start.isoformat()
    report["period_end"] = datetime.now(timezone.utc).isoformat()
    return report


@router.post("/operations/alerts", dependencies=[Depends(require_permission("design:analytics"))])
async def create_design_operations_alert(request: dict[str, Any], db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    alert_type = str(request.get("alert_type") or "design_alert")
    source = str(request.get("source") or "manual")
    message = str(request.get("message") or "Design workflow issue requires attention.")
    details = request.get("details") if isinstance(request.get("details"), dict) else {}
    severity = str(request.get("severity") or "warning")
    _raise_design_alert(db, alert_type, source, message, details, severity)
    db.commit()
    return {"status": "alert_recorded", "alert_type": alert_type, "source": source, "severity": severity}


@router.get("/funnels/{funnel_id}/metrics", dependencies=[Depends(require_permission("design:analytics"))])
async def list_funnel_metrics(funnel_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    if not _has_scope(db, current_user.id, "design:manage") and funnel.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the funnel owner or a Designer can view metrics")
    measurements = db.query(DesignFunnelMeasurement).filter(DesignFunnelMeasurement.funnel_id == funnel_id).order_by(DesignFunnelMeasurement.observed_at.desc()).limit(500).all()
    return {"funnel_id": str(funnel.id), "measurements": [{"id": str(item.id), "variant_id": str(item.variant_id) if item.variant_id else None, "event_type": item.event_type, "conversion_event": item.conversion_event, "source": item.source, "provider": item.provider, "campaign_name": item.campaign_name, "session_key": item.session_key, "referral_url": item.referral_url, "details": item.details, "conversion_value": item.conversion_value, "observed_at": item.observed_at.isoformat() if item.observed_at else None} for item in measurements]}


@router.post("/funnels/{funnel_id}/measurements", dependencies=[Depends(require_permission("design:analytics"))])
async def record_funnel_measurement(funnel_id: UUID, request: FunnelMeasurementCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    if request.variant_id:
        variant = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.id == request.variant_id, DesignFunnelVariant.funnel_id == funnel_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail="Variant does not belong to this funnel")
    if request.event_type == "conversion" and not request.conversion_event:
        raise HTTPException(status_code=422, detail="Conversion events require a conversion_event value")
    if request.provider not in {"webflow", "manual", "ghl", "canva"}:
        raise HTTPException(status_code=422, detail="Unsupported provider for funnel measurement")
    measurement = DesignFunnelMeasurement(
        funnel_id=funnel.id,
        variant_id=request.variant_id,
        source=request.source,
        provider=request.provider,
        campaign_name=request.campaign_name,
        session_key=request.session_key,
        referral_url=request.referral_url,
        event_type=request.event_type,
        conversion_event=request.conversion_event,
        conversion_value=int(request.details.get("value", 0) or 0),
        details=request.details,
    )
    db.add(measurement)
    db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=request.variant_id, actor_id=current_user.id, event_type="measurement_recorded", details={"measurement_id": str(measurement.id), "event_type": request.event_type, "conversion_event": request.conversion_event, "source": request.source}))
    db.commit()
    return {"id": str(measurement.id), "funnel_id": str(funnel.id), "status": "recorded"}


@router.post("/funnels/{funnel_id}/experiments", dependencies=[Depends(require_permission("design:analytics"))])
async def create_funnel_experiment(funnel_id: UUID, request: FunnelExperimentCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    if not funnel:
        raise HTTPException(status_code=404, detail="Funnel not found")
    if funnel.owner_id != current_user.id and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Only the funnel owner or a Designer/CEO can start an experiment")
    control = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.id == request.control_variant_id, DesignFunnelVariant.funnel_id == funnel.id).first()
    treatment = db.query(DesignFunnelVariant).filter(DesignFunnelVariant.id == request.treatment_variant_id, DesignFunnelVariant.funnel_id == funnel.id).first()
    if not control or not treatment:
        raise HTTPException(status_code=404, detail="Both experiment variants must belong to the funnel")
    if control.id == treatment.id:
        raise HTTPException(status_code=422, detail="Control and treatment variants must be different")
    experiment = DesignFunnelExperiment(
        funnel_id=funnel.id,
        name=request.name,
        goal_event=request.goal_event,
        hypothesis=request.hypothesis,
        status="draft",
        traffic_split=request.traffic_split,
        control_variant_id=control.id,
        treatment_variant_id=treatment.id,
        created_by=current_user.id,
        notes=request.notes,
    )
    db.add(experiment)
    db.add(DesignFunnelEvent(funnel_id=funnel.id, variant_id=treatment.id, actor_id=current_user.id, event_type="experiment_created", details={"experiment_id": str(experiment.id), "goal_event": request.goal_event, "traffic_split": request.traffic_split}))
    db.commit()
    return {"id": str(experiment.id), "status": experiment.status, "goal_event": experiment.goal_event, "traffic_split": experiment.traffic_split}


@router.post("/funnels/{funnel_id}/experiments/{experiment_id}/approve", dependencies=[Depends(require_permission("design:review_marketing"))])
async def approve_funnel_experiment(funnel_id: UUID, experiment_id: UUID, note: str = Query(..., min_length=5, max_length=2000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    experiment = db.query(DesignFunnelExperiment).filter(DesignFunnelExperiment.id == experiment_id, DesignFunnelExperiment.funnel_id == funnel_id).first()
    if not funnel or not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.status not in {"draft", "paused"}:
        raise HTTPException(status_code=409, detail="Only draft or paused experiments can be approved")
    experiment.status = "approved"
    experiment.approved_by = current_user.id
    experiment.approved_at = datetime.now(timezone.utc)
    experiment.notes = (experiment.notes or "") + f"\nApproved by {current_user.id}: {note}"
    db.add(DesignFunnelEvent(funnel_id=funnel.id, actor_id=current_user.id, event_type="experiment_approved", details={"experiment_id": str(experiment.id), "note": note}))
    db.commit()
    return {"id": str(experiment.id), "status": experiment.status, "approved_at": experiment.approved_at.isoformat()}


@router.post("/funnels/{funnel_id}/experiments/{experiment_id}/start", dependencies=[Depends(require_permission("design:analytics"))])
async def start_funnel_experiment(funnel_id: UUID, experiment_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    experiment = db.query(DesignFunnelExperiment).filter(DesignFunnelExperiment.id == experiment_id, DesignFunnelExperiment.funnel_id == funnel_id).first()
    if not funnel or not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.status != "approved":
        raise HTTPException(status_code=409, detail="Marketing review approval is required before starting an experiment")
    experiment.status = "running"
    experiment.started_at = datetime.now(timezone.utc)
    db.add(DesignFunnelEvent(funnel_id=funnel.id, actor_id=current_user.id, event_type="experiment_started", details={"experiment_id": str(experiment.id), "traffic_split": experiment.traffic_split}))
    db.commit()
    return {"id": str(experiment.id), "status": experiment.status, "started_at": experiment.started_at.isoformat()}


@router.post("/funnels/{funnel_id}/experiments/{experiment_id}/stop", dependencies=[Depends(require_permission("design:analytics"))])
async def stop_funnel_experiment(funnel_id: UUID, experiment_id: UUID, note: str = Query(..., min_length=5, max_length=2000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    funnel = db.query(DesignFunnel).filter(DesignFunnel.id == funnel_id).first()
    experiment = db.query(DesignFunnelExperiment).filter(DesignFunnelExperiment.id == experiment_id, DesignFunnelExperiment.funnel_id == funnel_id).first()
    if not funnel or not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.status not in {"running", "approved"}:
        raise HTTPException(status_code=409, detail="Only active experiments can be stopped")
    experiment.status = "paused"
    experiment.ended_at = datetime.now(timezone.utc)
    experiment.notes = (experiment.notes or "") + f"\nStopped by {current_user.id}: {note}"
    db.add(DesignFunnelEvent(funnel_id=funnel.id, actor_id=current_user.id, event_type="experiment_stopped", details={"experiment_id": str(experiment.id), "note": note}))
    db.commit()
    return {"id": str(experiment.id), "status": experiment.status, "ended_at": experiment.ended_at.isoformat()}


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
        _raise_design_alert(db, "webflow_publish_failed", "webflow", "Webflow funnel publication failed for the approved variant.", {"funnel_id": str(funnel.id), "variant_id": str(variant.id), "status_code": exc.status_code, "detail": str(exc.detail)}, "critical")
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


@router.get("/program-material-templates", dependencies=[Depends(require_permission("design:read_programs"))])
async def list_program_material_templates(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    templates = db.query(ProgramMaterialTemplate).filter(ProgramMaterialTemplate.status == "approved").order_by(ProgramMaterialTemplate.updated_at.desc()).all()
    return {"templates": [{
        "id": str(item.id),
        "template_key": item.template_key,
        "title": item.title,
        "category": item.category,
        "audience": item.audience,
        "provider": item.provider,
        "status": item.status,
        "allowed_fields": item.allowed_fields or [],
        "required_fields": item.required_fields or [],
        "usage_rights": item.usage_rights or {},
        "version": item.version,
    } for item in templates]}


@router.post("/program-material-templates", dependencies=[Depends(require_permission("design:templates"))])
async def create_program_material_template(request: ProgramMaterialTemplateCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    if request.audience not in {"programs", "student_success"} and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Program material templates for programs and student success are reserved for Designer and CEO owners")
    if not request.allowed_fields:
        raise HTTPException(status_code=422, detail="At least one allowed field is required")
    missing = set(request.required_fields) - set(request.allowed_fields)
    if missing:
        raise HTTPException(status_code=422, detail=f"Required fields must be included in allowed_fields: {sorted(missing)}")
    if request.template_json.get("type") not in {"workbook", "certificate", "visual_aid", "document", "tracking"}:
        raise HTTPException(status_code=422, detail="Template JSON is missing a recognized material type")
    template = ProgramMaterialTemplate(
        template_key=request.template_key,
        title=request.title,
        category=request.category,
        audience=request.audience,
        provider="manual",
        allowed_fields=request.allowed_fields,
        required_fields=request.required_fields,
        template_json=request.template_json,
        usage_rights=request.usage_rights,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(template)
    db.commit()
    return {"id": str(template.id), "template_key": template.template_key, "status": template.status, "version": template.version}


@router.post("/program-material-templates/{template_id}/approve", dependencies=[Depends(require_permission("design:review_programs"))])
async def approve_program_material_template(template_id: UUID, note: str = Query(..., min_length=5, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    template = db.query(ProgramMaterialTemplate).filter(ProgramMaterialTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Program material template not found")
    if template.status == "approved":
        raise HTTPException(status_code=409, detail="Template is already approved")
    template.status = "approved"
    template.approved_by = current_user.id
    template.approved_at = datetime.now(timezone.utc)
    template.updated_by = current_user.id
    _provider_event(db, "internal", "program_material_template", template.id, current_user.id, "approved", "success", {"note": note, "version": template.version})
    db.commit()
    return {"id": str(template.id), "status": template.status, "approved_at": template.approved_at.isoformat()}


@router.post("/program-material-templates/{template_id}/render", dependencies=[Depends(require_permission("design:read_programs"))])
async def render_program_material_template(template_id: UUID, request: ProgramMaterialRenderRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    template = db.query(ProgramMaterialTemplate).filter(ProgramMaterialTemplate.id == template_id).first()
    if not template or template.status != "approved":
        raise HTTPException(status_code=404, detail="Approved program material template not found")
    if request.allow_pii and template.audience not in {"programs", "student_success"}:
        raise HTTPException(status_code=403, detail="PII rendering is limited to Program or Student Success templates")
    allowed = set(template.allowed_fields or [])
    request_fields = set((request.data or {}).keys())
    if not request_fields.issubset(allowed):
        raise HTTPException(status_code=422, detail="Render data includes fields outside the approved template schema")
    missing = set(template.required_fields or []) - request_fields
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required material fields: {sorted(missing)}")
    if request.allow_pii and not template.audience in {"programs", "student_success"}:
        raise HTTPException(status_code=403, detail="This template does not permit student-specific data")
    rendered = json.loads(json.dumps(template.template_json))
    for field_name, value in (request.data or {}).items():
        if field_name in rendered:
            rendered[field_name] = value
    instance = ProgramMaterialInstance(
        template_id=template.id,
        title=request.data.get("title", template.title),
        audience=template.audience,
        status="draft",
        payload={"template_key": template.template_key, "rendered": rendered, "allow_pii": request.allow_pii},
        allow_student_pii="true" if request.allow_pii else "false",
        created_by=current_user.id,
    )
    db.add(instance)
    db.commit()
    return {"id": str(instance.id), "template_id": str(template.id), "status": instance.status, "payload": instance.payload}


@router.post("/program-material-templates/{template_id}/publish", dependencies=[Depends(require_permission("design:publish_programs"))])
async def publish_program_material_template(template_id: UUID, request: ProgramMaterialRenderRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    template = db.query(ProgramMaterialTemplate).filter(ProgramMaterialTemplate.id == template_id).first()
    if not template or template.status != "approved":
        raise HTTPException(status_code=404, detail="Approved program material template not found")
    if request.allow_pii and template.audience not in {"programs", "student_success"}:
        raise HTTPException(status_code=403, detail="PII publishing is limited to Program or Student Success templates")
    instance = ProgramMaterialInstance(
        template_id=template.id,
        title=request.data.get("title", template.title),
        audience=template.audience,
        status="published",
        payload={"template_key": template.template_key, "rendered": template.template_json, "allow_pii": request.allow_pii, "data": request.data},
        allow_student_pii="true" if request.allow_pii else "false",
        created_by=current_user.id,
        published_by=current_user.id,
        published_at=datetime.now(timezone.utc),
    )
    db.add(instance)
    db.commit()
    return {"id": str(instance.id), "status": instance.status, "template_id": str(template.id)}
