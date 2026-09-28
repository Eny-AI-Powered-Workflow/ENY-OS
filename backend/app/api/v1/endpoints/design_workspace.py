# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/design_workspace.py

import json
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.design_system import (
    DesignAsset,
    DesignAssetEvent,
    DesignAssetFile,
    DesignAssetVersion,
    DesignRequest,
    DesignRequestEvent,
    DesignSystemDocument,
    DesignTemplate,
    DesignTemplateEvent,
    DesignTemplateVersion,
    DesignTemplateVersion,
)
from app.models.marketing_content import MarketingContentItem
from app.models.marketing_intelligence import MarketingVideoAsset
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.services.design_asset_service import design_asset_service

router = APIRouter()
Audience = Literal["shared", "marketing", "programs", "student_success"]


class DesignRequestCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=240)
    brief: str = Field(..., min_length=10, max_length=10000)
    request_type: Literal["social_graphic", "email_header", "webinar_promotion", "video_thumbnail", "quote_card", "certificate", "program_material", "funnel_asset", "other"]
    audience: Audience
    due_at: Optional[datetime] = None
    campaign_name: Optional[str] = Field(None, max_length=240)
    program_name: Optional[str] = Field(None, max_length=240)
    source_content_id: Optional[UUID] = None
    source_video_asset_id: Optional[UUID] = None
    reference_urls: list[str] = Field(default_factory=list, max_length=30)


class DesignRequestUpdate(BaseModel):
    owner_id: Optional[UUID] = None
    due_at: Optional[datetime] = None
    status: Literal["in_progress", "in_review"]
    note: str = Field(..., min_length=3, max_length=1000)


class TemplateCreate(BaseModel):
    template_key: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9][a-z0-9._-]+$")
    title: str = Field(..., min_length=3, max_length=240)
    category: str = Field(..., min_length=2, max_length=80)
    audience: Audience
    provider: Literal["manual_canva", "manual_upload"] = "manual_canva"
    provider_template_id: Optional[str] = Field(None, max_length=240)
    template_url: Optional[str] = Field(None, max_length=2000)
    base_brand_document_id: UUID
    base_brand_version: int = Field(..., ge=1)
    locked_fields: list[str] = Field(default_factory=list, max_length=100)
    locked_values: dict[str, Any] = Field(default_factory=dict)
    editable_fields: list[str] = Field(default_factory=list, max_length=100)
    usage_rights: dict[str, Any] = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=240)
    category: Optional[str] = Field(None, min_length=2, max_length=80)
    template_url: Optional[str] = Field(None, max_length=2000)
    provider_template_id: Optional[str] = Field(None, max_length=240)
    base_brand_document_id: Optional[UUID] = None
    base_brand_version: Optional[int] = Field(None, ge=1)
    locked_fields: Optional[list[str]] = Field(None, max_length=100)
    locked_values: Optional[dict[str, Any]] = None
    editable_fields: Optional[list[str]] = Field(None, max_length=100)
    usage_rights: Optional[dict[str, Any]] = None
    change_note: str = Field(..., min_length=3, max_length=1000)


class WorkflowReview(BaseModel):
    note: str = Field(..., min_length=5, max_length=2000)
    source_verified: bool = False


class AssetRevision(BaseModel):
    title: str = Field(..., min_length=3, max_length=240)
    usage_rights: dict[str, Any]
    change_note: str = Field(..., min_length=3, max_length=1000)


class UsageRights(BaseModel):
    rights_basis: str = Field(..., min_length=3, max_length=500)
    permitted_uses: list[str] = Field(..., min_length=1, max_length=30)
    attribution: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


def _has_scope(db: Session, user_id: UUID, scope: str) -> bool:
    return db.query(Permission.id).join(RolePermission, Permission.id == RolePermission.permission_id).join(
        UserRole, RolePermission.role_id == UserRole.role_id
    ).filter(UserRole.user_id == user_id, Permission.scope == scope).first() is not None


def _validate_audience_access(db: Session, user_id: UUID, audience: str, *, action: str) -> None:
    if _has_scope(db, user_id, "design:manage"):
        return
    required = {
        ("request", "marketing"): "design:read_marketing",
        ("request", "programs"): "design:read_programs",
        ("request", "student_success"): "design:read_programs",
        ("review", "marketing"): "design:review_marketing",
        ("review", "programs"): "design:review_programs",
        ("review", "student_success"): "design:review_programs",
        ("publish", "marketing"): "design:publish_marketing",
        ("publish", "programs"): "design:publish_programs",
        ("publish", "student_success"): "design:publish_programs",
    }.get((action, audience))
    if audience == "shared" or not required or not _has_scope(db, user_id, required):
        raise HTTPException(status_code=403, detail="This role cannot perform that action for the selected audience")


def _visible_asset_query(db: Session, user_id: UUID):
    if _has_scope(db, user_id, "design:manage"):
        return db.query(DesignAsset)
    filters = []
    if _has_scope(db, user_id, "design:read_marketing"):
        filters.append((DesignAsset.audience.in_(["marketing", "shared"])) & (DesignAsset.status.in_(["approved", "published"])))
    if _has_scope(db, user_id, "design:review_marketing"):
        filters.append((DesignAsset.audience == "marketing") & (DesignAsset.status == "in_review"))
    if _has_scope(db, user_id, "design:read_programs"):
        filters.append((DesignAsset.audience.in_(["programs", "student_success", "shared"])) & (DesignAsset.status.in_(["approved", "published"])))
    if _has_scope(db, user_id, "design:review_programs"):
        filters.append((DesignAsset.audience.in_(["programs", "student_success"])) & (DesignAsset.status == "in_review"))
    if not filters:
        raise HTTPException(status_code=403, detail="No design assets are available to this account")
    return db.query(DesignAsset).filter(or_(*filters))


def _visible_template_query(db: Session, user_id: UUID):
    if _has_scope(db, user_id, "design:manage"):
        return db.query(DesignTemplate)
    filters = []
    if _has_scope(db, user_id, "design:templates"):
        filters.append((DesignTemplate.audience.in_(["marketing", "shared"])) & (DesignTemplate.status == "approved"))
    if _has_scope(db, user_id, "design:read_programs"):
        filters.append((DesignTemplate.audience.in_(["programs", "student_success", "shared"])) & (DesignTemplate.status == "approved"))
    if _has_scope(db, user_id, "design:review_marketing"):
        filters.append((DesignTemplate.audience == "marketing") & (DesignTemplate.status == "in_review"))
    if _has_scope(db, user_id, "design:review_programs"):
        filters.append((DesignTemplate.audience.in_(["programs", "student_success"])) & (DesignTemplate.status == "in_review"))
    if not filters:
        raise HTTPException(status_code=403, detail="No templates are available to this account")
    return db.query(DesignTemplate).filter(or_(*filters))


def _brand_document(db: Session, document_id: UUID, version: int, audience: str) -> DesignSystemDocument:
    document = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == document_id).first()
    if not document or document.status != "approved" or document.source_status != "verified":
        raise HTTPException(status_code=409, detail="Assets and templates require approved, source-verified brand guidance")
    if document.version != version:
        raise HTTPException(status_code=409, detail="Selected brand guidance version is stale; refresh and select the approved current version")
    if document.audience not in {audience, "shared"}:
        raise HTTPException(status_code=422, detail="Brand guidance audience does not match the requested asset/template audience")
    return document


def _template_payload(db: Session, template: DesignTemplate) -> dict[str, Any]:
    brand = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == template.base_brand_document_id).first()
    return {
        "id": str(template.id), "template_key": template.template_key, "title": template.title,
        "category": template.category, "audience": template.audience, "provider": template.provider,
        "provider_template_id": template.provider_template_id, "template_url": template.template_url,
        "status": template.status, "version": template.version,
        "base_brand_document_id": str(template.base_brand_document_id), "base_brand_version": template.base_brand_version,
        "brand_current_version": brand.version if brand else None,
        "stale": not brand or brand.status != "approved" or brand.version != template.base_brand_version,
        "locked_fields": template.locked_fields or [], "locked_values": template.locked_values or {}, "editable_fields": template.editable_fields or [],
        "usage_rights": template.usage_rights or {}, "approved_at": template.approved_at.isoformat() if template.approved_at else None,
    }


def _asset_payload(db: Session, asset: DesignAsset, include_files: bool = True) -> dict[str, Any]:
    brand = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == asset.brand_document_id).first()
    template = db.query(DesignTemplate).filter(DesignTemplate.id == asset.template_id).first() if asset.template_id else None
    files = db.query(DesignAssetFile).filter(DesignAssetFile.asset_id == asset.id).order_by(DesignAssetFile.created_at.desc()).all() if include_files else []
    return {
        "id": str(asset.id), "title": asset.title, "asset_type": asset.asset_type,
        "audience": asset.audience, "status": asset.status, "provider": asset.provider,
        "request_id": str(asset.request_id) if asset.request_id else None,
        "template_id": str(asset.template_id) if asset.template_id else None,
        "template_version": asset.template_version,
        "locked_values_snapshot": asset.locked_values_snapshot or {}, "variant_values": asset.variant_values or {},
        "template_stale": bool(template and (template.status != "approved" or template.version != asset.template_version)),
        "brand_document_id": str(asset.brand_document_id), "brand_version": asset.brand_version,
        "brand_stale": not brand or brand.status != "approved" or brand.version != asset.brand_version,
        "campaign_name": asset.campaign_name, "program_name": asset.program_name,
        "source_content_id": str(asset.source_content_id) if asset.source_content_id else None,
        "source_video_asset_id": str(asset.source_video_asset_id) if asset.source_video_asset_id else None,
        "usage_rights": asset.usage_rights or {}, "revision": asset.revision,
        "approved_by": str(asset.approved_by) if asset.approved_by else None,
        "approved_at": asset.approved_at.isoformat() if asset.approved_at else None,
        "published_by": str(asset.published_by) if asset.published_by else None,
        "published_at": asset.published_at.isoformat() if asset.published_at else None,
        "files": [{"id": str(file.id), "file_kind": file.file_kind, "provider": file.provider, "original_filename": file.original_filename, "mime_type": file.mime_type, "size_bytes": file.size_bytes, "created_at": file.created_at.isoformat() if file.created_at else None} for file in files],
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


def _snapshot_asset(asset: DesignAsset) -> dict[str, Any]:
    return {
        "title": asset.title, "asset_type": asset.asset_type, "provider": asset.provider, "audience": asset.audience,
        "status": asset.status, "request_id": str(asset.request_id) if asset.request_id else None,
        "template_id": str(asset.template_id) if asset.template_id else None,
        "template_version": asset.template_version, "brand_document_id": str(asset.brand_document_id),
        "locked_values_snapshot": asset.locked_values_snapshot or {}, "variant_values": asset.variant_values or {},
        "brand_version": asset.brand_version, "usage_rights": asset.usage_rights or {}, "revision": asset.revision,
    }


def _validate_template_snapshot(db: Session, asset: DesignAsset) -> None:
    if not asset.template_id:
        return
    template = db.query(DesignTemplate).filter(DesignTemplate.id == asset.template_id).first()
    if not template or template.status != "approved" or template.version != asset.template_version:
        raise HTTPException(status_code=409, detail="The linked template version is no longer current and approved")
    if template.base_brand_document_id != asset.brand_document_id or template.base_brand_version != asset.brand_version:
        raise HTTPException(status_code=409, detail="The asset and template are bound to different brand versions")
    if (template.locked_values or {}) != (asset.locked_values_snapshot or {}):
        raise HTTPException(status_code=409, detail="Locked template values changed; create a new derivative and review it")
    locked_fields = set(template.locked_fields or [])
    editable_fields = set(template.editable_fields or [])
    if locked_fields & set(asset.variant_values or {}) or set(asset.variant_values or {}) - editable_fields:
        raise HTTPException(status_code=409, detail="Variant values conflict with locked or undeclared template fields")


def _validate_template_rights_payload(rights: dict[str, Any]) -> None:
    if not rights.get("rights_basis") or not rights.get("permitted_uses"):
        raise HTTPException(status_code=422, detail="Template requires a documented rights basis and permitted uses")


def _validate_template_rights(template: DesignTemplate) -> None:
    _validate_template_rights_payload(template.usage_rights or {})


def _validate_asset_usage_rights(asset: DesignAsset) -> None:
    try:
        rights = UsageRights.model_validate(asset.usage_rights or {})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Asset usage rights are incomplete") from exc
    expires_at = rights.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Asset usage rights have expired")


@router.post("/requests", dependencies=[Depends(require_permission("design:request"))])
async def create_design_request(request: DesignRequestCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    _validate_audience_access(db, current_user.id, request.audience, action="request")
    if request.audience == "shared" and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Shared requests are reserved for Designer and CEO owners")
    if request.source_content_id:
        if request.audience != "marketing":
            raise HTTPException(status_code=403, detail="Marketing content may only be linked to Marketing design requests")
        source = db.query(MarketingContentItem).filter(MarketingContentItem.id == request.source_content_id).first()
        if not source or source.status not in {"approved", "published"}:
            raise HTTPException(status_code=409, detail="Only approved or published Marketing content can be linked to a design request")
    if request.source_video_asset_id:
        if request.audience != "marketing":
            raise HTTPException(status_code=403, detail="Marketing video packs may only be linked to Marketing design requests")
        source_video = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == request.source_video_asset_id).first()
        if not source_video or source_video.status != "pack_generated":
            raise HTTPException(status_code=409, detail="Only processed video assets can be linked to a design request")
    design_request = DesignRequest(**request.model_dump(), requester_id=current_user.id)
    db.add(design_request)
    db.flush()
    db.add(DesignRequestEvent(request_id=design_request.id, actor_id=current_user.id, event_type="requested", details={"audience": request.audience, "request_type": request.request_type}))
    db.commit()
    return {"id": str(design_request.id), "title": design_request.title, "status": design_request.status, "audience": design_request.audience, "due_at": design_request.due_at.isoformat() if design_request.due_at else None}


@router.get("/requests", dependencies=[Depends(require_permission("design:workspace"))])
async def list_design_requests(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    query = db.query(DesignRequest)
    if not _has_scope(db, current_user.id, "design:manage"):
        query = query.filter(DesignRequest.requester_id == current_user.id)
    requests = query.order_by(DesignRequest.due_at.asc().nullslast(), DesignRequest.created_at.desc()).limit(300).all()
    return {"requests": [{"id": str(item.id), "title": item.title, "brief": item.brief, "request_type": item.request_type, "audience": item.audience, "status": item.status, "requester_id": str(item.requester_id), "owner_id": str(item.owner_id) if item.owner_id else None, "due_at": item.due_at.isoformat() if item.due_at else None, "campaign_name": item.campaign_name, "program_name": item.program_name, "source_content_id": str(item.source_content_id) if item.source_content_id else None, "source_video_asset_id": str(item.source_video_asset_id) if item.source_video_asset_id else None, "reference_urls": item.reference_urls or [], "created_at": item.created_at.isoformat() if item.created_at else None} for item in requests]}


@router.get("/requests/{request_id}/history", dependencies=[Depends(require_permission("design:workspace"))])
async def get_design_request_history(request_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    item = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not item or (item.requester_id != current_user.id and not _has_scope(db, current_user.id, "design:manage")):
        raise HTTPException(status_code=404, detail="Design request not found")
    events = db.query(DesignRequestEvent).filter(DesignRequestEvent.request_id == item.id).order_by(DesignRequestEvent.created_at.desc()).all()
    return {"events": [{"event_type": event.event_type, "details": event.details, "actor_id": str(event.actor_id), "created_at": event.created_at.isoformat() if event.created_at else None} for event in events]}


@router.patch("/requests/{request_id}", dependencies=[Depends(require_permission("design:manage"))])
async def update_design_request(request_id: UUID, request: DesignRequestUpdate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    item = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Design request not found")
    previous = item.status
    item.owner_id = request.owner_id
    item.due_at = request.due_at
    item.status = request.status
    db.add(DesignRequestEvent(request_id=item.id, actor_id=current_user.id, event_type="assigned_or_status_changed", details={"from": previous, "to": item.status, "owner_id": str(item.owner_id) if item.owner_id else None, "due_at": item.due_at.isoformat() if item.due_at else None, "note": request.note}))
    db.commit()
    return {"id": str(item.id), "status": item.status, "owner_id": str(item.owner_id) if item.owner_id else None}


@router.post("/requests/{request_id}/cancel", dependencies=[Depends(require_permission("design:workspace"))])
async def cancel_design_request(request_id: UUID, note: str = Form(..., min_length=3, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    item = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Design request not found")
    if item.requester_id != current_user.id and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Only the requester or Designer owner can cancel this request")
    if item.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Completed or cancelled requests cannot be changed")
    item.status = "cancelled"
    db.add(DesignRequestEvent(request_id=item.id, actor_id=current_user.id, event_type="cancelled", details={"note": note}))
    db.commit()
    return {"id": str(item.id), "status": item.status}


@router.get("/templates", dependencies=[Depends(require_permission("design:workspace"))])
async def list_design_templates(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    templates = _visible_template_query(db, current_user.id).order_by(DesignTemplate.audience, DesignTemplate.category, DesignTemplate.title).limit(300).all()
    return {"templates": [_template_payload(db, item) for item in templates]}


@router.get("/templates/{template_id}/history", dependencies=[Depends(require_permission("design:workspace"))])
async def get_design_template_history(template_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    template = _visible_template_query(db, current_user.id).filter(DesignTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Design template not found")
    versions = db.query(DesignTemplateVersion).filter(DesignTemplateVersion.template_id == template_id).order_by(DesignTemplateVersion.version.desc()).all()
    events = db.query(DesignTemplateEvent).filter(DesignTemplateEvent.template_id == template_id).order_by(DesignTemplateEvent.created_at.desc()).all()
    return {"versions": [{"version": item.version, "snapshot": item.snapshot, "change_note": item.change_note, "changed_by": str(item.changed_by), "created_at": item.created_at.isoformat() if item.created_at else None} for item in versions], "events": [{"event_type": item.event_type, "details": item.details, "actor_id": str(item.actor_id), "created_at": item.created_at.isoformat() if item.created_at else None} for item in events]}


@router.post("/templates", dependencies=[Depends(require_permission("design:templates"))])
async def create_design_template(request: TemplateCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    if request.audience == "shared" and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Shared templates are reserved for Designer and CEO owners")
    if request.audience == "marketing" and not (_has_scope(db, current_user.id, "design:manage") or _has_scope(db, current_user.id, "design:review_marketing")):
        raise HTTPException(status_code=403, detail="This role cannot create Marketing templates")
    if request.audience in {"programs", "student_success"} and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Program templates are managed by Designer or CEO")
    _brand_document(db, request.base_brand_document_id, request.base_brand_version, request.audience)
    if not request.template_url and not request.provider_template_id:
        raise HTTPException(status_code=422, detail="Add the Canva template URL or provider template ID")
    if request.template_url and not request.template_url.lower().startswith("https://"):
        raise HTTPException(status_code=422, detail="Template URLs must use HTTPS")
    if set(request.locked_fields) & set(request.editable_fields):
        raise HTTPException(status_code=422, detail="A template field cannot be both locked and editable")
    if set(request.locked_fields) != set(request.locked_values):
        raise HTTPException(status_code=422, detail="Locked values must define exactly the declared locked template fields")
    if request.template_url and not request.template_url.lower().startswith("https://"):
        raise HTTPException(status_code=422, detail="Template URLs must use HTTPS")
    _validate_template_rights_payload(request.usage_rights)
    existing = db.query(DesignTemplate.id).filter(DesignTemplate.template_key == request.template_key, DesignTemplate.audience == request.audience).first()
    if existing:
        raise HTTPException(status_code=409, detail="A template with this key already exists for the audience")
    template = DesignTemplate(**request.model_dump(), created_by=current_user.id, updated_by=current_user.id)
    db.add(template)
    db.flush()
    db.add(DesignTemplateEvent(template_id=template.id, actor_id=current_user.id, event_type="created", details={"audience": template.audience, "brand_version": template.base_brand_version, "locked_fields": template.locked_fields}))
    db.commit()
    return _template_payload(db, template)


@router.patch("/templates/{template_id}", dependencies=[Depends(require_permission("design:templates"))])
async def update_design_template(template_id: UUID, request: TemplateUpdate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    template = db.query(DesignTemplate).filter(DesignTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Design template not found")
    if not _has_scope(db, current_user.id, "design:manage") and not (template.audience == "marketing" and _has_scope(db, current_user.id, "design:templates")):
        raise HTTPException(status_code=403, detail="This role cannot edit the selected template audience")
    if template.status == "archived":
        raise HTTPException(status_code=409, detail="Archived templates cannot be revised")
    values = request.model_dump(exclude_unset=True, exclude={"change_note"})
    brand_id = values.get("base_brand_document_id", template.base_brand_document_id)
    brand_version = values.get("base_brand_version", template.base_brand_version)
    _brand_document(db, brand_id, brand_version, template.audience)
    locked_fields = values.get("locked_fields", template.locked_fields or [])
    locked_values = values.get("locked_values", template.locked_values or {})
    editable_fields = values.get("editable_fields", template.editable_fields or [])
    if set(locked_fields) & set(editable_fields):
        raise HTTPException(status_code=422, detail="A template field cannot be both locked and editable")
    if set(locked_fields) != set(locked_values):
        raise HTTPException(status_code=422, detail="Locked values must define exactly the declared locked template fields")
    if values.get("template_url") and not values["template_url"].lower().startswith("https://"):
        raise HTTPException(status_code=422, detail="Template URLs must use HTTPS")
    _validate_template_rights_payload(values.get("usage_rights") or template.usage_rights or {})
    if not (values.get("template_url", template.template_url) or values.get("provider_template_id", template.provider_template_id)):
        raise HTTPException(status_code=422, detail="Template revision must retain a Canva URL or provider template ID")
    snapshot = _template_payload(db, template)
    db.add(DesignTemplateVersion(template_id=template.id, version=template.version, snapshot=snapshot, change_note=request.change_note, changed_by=current_user.id))
    for key, value in values.items():
        setattr(template, key, value)
    template.version += 1
    template.status = "draft"
    template.approved_by = None
    template.approved_at = None
    template.updated_by = current_user.id
    db.add(DesignTemplateEvent(template_id=template.id, actor_id=current_user.id, event_type="edited", details={"version": template.version, "note": request.change_note, "locked_fields": template.locked_fields}))
    db.commit()
    return _template_payload(db, template)


@router.post("/templates/{template_id}/submit", dependencies=[Depends(require_permission("design:templates"))])
async def submit_design_template(template_id: UUID, note: str = Form(..., min_length=3, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    template = db.query(DesignTemplate).filter(DesignTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Design template not found")
    if template.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft templates can be submitted")
    _brand_document(db, template.base_brand_document_id, template.base_brand_version, template.audience)
    template.status = "in_review"
    template.updated_by = current_user.id
    db.add(DesignTemplateEvent(template_id=template.id, actor_id=current_user.id, event_type="submitted_for_review", details={"note": note, "version": template.version}))
    db.commit()
    return _template_payload(db, template)


async def _review_template(template_id: UUID, request: WorkflowReview, db: Session, current_user: Any, audience: str, approve: bool):
    template = db.query(DesignTemplate).filter(DesignTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Design template not found")
    _validate_audience_access(db, current_user.id, template.audience, action="review")
    if template.status != "in_review":
        raise HTTPException(status_code=409, detail="Only templates in review can be decided")
    if approve:
        _brand_document(db, template.base_brand_document_id, template.base_brand_version, template.audience)
        _validate_template_rights(template)
        if not request.source_verified:
            raise HTTPException(status_code=422, detail="Approval requires verified brand source and documented template usage rights")
        template.status = "approved"
        template.approved_by = current_user.id
        template.approved_at = datetime.now(timezone.utc)
    else:
        template.status = "draft"
        template.approved_by = None
        template.approved_at = None
    template.updated_by = current_user.id
    db.add(DesignTemplateEvent(template_id=template.id, actor_id=current_user.id, event_type="approved" if approve else "changes_requested", details={"note": request.note, "source_verified": request.source_verified if approve else False, "version": template.version}))
    db.commit()
    return _template_payload(db, template)


@router.post("/templates/{template_id}/approve-marketing", dependencies=[Depends(require_permission("design:review_marketing"))])
async def approve_marketing_template(template_id: UUID, request: WorkflowReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _review_template(template_id, request, db, current_user, "marketing", True)


@router.post("/templates/{template_id}/approve-programs", dependencies=[Depends(require_permission("design:review_programs"))])
async def approve_program_template(template_id: UUID, request: WorkflowReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _review_template(template_id, request, db, current_user, "programs", True)


@router.post("/templates/{template_id}/request-marketing-changes", dependencies=[Depends(require_permission("design:review_marketing"))])
async def request_marketing_template_changes(template_id: UUID, request: WorkflowReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _review_template(template_id, request, db, current_user, "marketing", False)


@router.post("/templates/{template_id}/request-program-changes", dependencies=[Depends(require_permission("design:review_programs"))])
async def request_program_template_changes(template_id: UUID, request: WorkflowReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _review_template(template_id, request, db, current_user, "programs", False)


@router.post("/assets", dependencies=[Depends(require_permission("design:write"))])
async def create_design_asset(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=3, max_length=240),
    asset_type: str = Form(..., min_length=2, max_length=80),
    audience: Audience = Form(...),
    brand_document_id: UUID = Form(...),
    brand_version: int = Form(..., ge=1),
    usage_rights_json: str = Form(...),
    file_kind: Literal["source", "export", "preview"] = Form("export"),
    request_id: Optional[UUID] = Form(None),
    template_id: Optional[UUID] = Form(None),
    template_version: Optional[int] = Form(None),
    variant_values_json: str = Form("{}"),
    campaign_name: Optional[str] = Form(None, max_length=240),
    program_name: Optional[str] = Form(None, max_length=240),
    source_content_id: Optional[UUID] = Form(None),
    source_video_asset_id: Optional[UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    _validate_audience_access(db, current_user.id, audience, action="request")
    if audience == "shared" and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Shared assets are reserved for Designer and CEO owners")
    try:
        rights = UsageRights.model_validate(json.loads(usage_rights_json))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Usage rights must be valid JSON with a rights_basis and permitted_uses") from exc
    try:
        variant_values = json.loads(variant_values_json)
        if not isinstance(variant_values, dict):
            raise ValueError("variant values must be an object")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Variant values must be a JSON object") from exc
    _brand_document(db, brand_document_id, brand_version, audience)
    if request_id:
        request_row = db.query(DesignRequest).filter(DesignRequest.id == request_id).first()
        if not request_row or request_row.status in {"completed", "cancelled"} or request_row.audience != audience:
            raise HTTPException(status_code=409, detail="Linked design request is missing, closed, or has a different audience")
    if template_id:
        template = db.query(DesignTemplate).filter(DesignTemplate.id == template_id).first()
        if not template or template.status != "approved" or template.version != template_version:
            raise HTTPException(status_code=409, detail="Only the current approved template version can be used")
        if template.audience not in {audience, "shared"} or template.base_brand_document_id != brand_document_id or template.base_brand_version != brand_version:
            raise HTTPException(status_code=409, detail="Asset audience or brand version does not match its approved template")
        locked_fields = set(template.locked_fields or [])
        editable_fields = set(template.editable_fields or [])
        if locked_fields - set(template.locked_values or {}):
            raise HTTPException(status_code=409, detail="Template locked values are incomplete; repair and reapprove the template")
        if set(variant_values) & locked_fields:
            raise HTTPException(status_code=422, detail="Variant values cannot override locked template fields")
        if set(variant_values) - editable_fields:
            raise HTTPException(status_code=422, detail="Variant values may only populate declared editable template fields")
    if source_content_id:
        if audience != "marketing":
            raise HTTPException(status_code=403, detail="Marketing content may only be linked to Marketing assets")
        source_content = db.query(MarketingContentItem).filter(MarketingContentItem.id == source_content_id).first()
        if not source_content or source_content.status not in {"approved", "published"}:
            raise HTTPException(status_code=409, detail="Only approved or published Marketing content can be linked")
    if source_video_asset_id:
        if audience != "marketing":
            raise HTTPException(status_code=403, detail="Marketing video packs may only be linked to Marketing assets")
        source_video = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == source_video_asset_id).first()
        if not source_video or source_video.status != "pack_generated":
            raise HTTPException(status_code=409, detail="Only processed video content packs can be linked")
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)
    storage_path = await design_asset_service.upload(file, size_bytes, audience)
    asset = DesignAsset(
        title=title.strip(), asset_type=asset_type.strip(), audience=audience,
        provider="manual_canva" if template_id else "manual_upload",
        request_id=request_id, template_id=template_id, template_version=template_version,
        locked_values_snapshot=(template.locked_values or {}) if template_id else {}, variant_values=variant_values,
        brand_document_id=brand_document_id, brand_version=brand_version,
        campaign_name=campaign_name, program_name=program_name,
        source_content_id=source_content_id, source_video_asset_id=source_video_asset_id,
        usage_rights=rights.model_dump(mode="json"), created_by=current_user.id, updated_by=current_user.id,
    )
    db.add(asset)
    db.flush()
    file_row = DesignAssetFile(asset_id=asset.id, file_kind=file_kind, provider=asset.provider, original_filename=file.filename or "design-asset", mime_type=file.content_type or "application/octet-stream", size_bytes=size_bytes, storage_path=storage_path, created_by=current_user.id)
    db.add(file_row)
    db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="created", details={"file_id": str(file_row.id), "file_kind": file_kind, "brand_version": brand_version, "template_id": str(template_id) if template_id else None, "template_version": template_version}))
    db.commit()
    return _asset_payload(db, asset)


@router.get("/assets", dependencies=[Depends(require_permission("design:workspace"))])
async def list_design_assets(
    source_content_id: Optional[UUID] = Query(None),
    source_video_asset_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    query = _visible_asset_query(db, current_user.id)
    if source_content_id:
        query = query.filter(DesignAsset.source_content_id == source_content_id)
    if source_video_asset_id:
        query = query.filter(DesignAsset.source_video_asset_id == source_video_asset_id)
    assets = query.order_by(DesignAsset.updated_at.desc()).limit(300).all()
    return {"assets": [_asset_payload(db, asset) for asset in assets]}


@router.post("/assets/{asset_id}/files", dependencies=[Depends(require_permission("design:write"))])
async def add_design_asset_file(asset_id: UUID, file: UploadFile = File(...), file_kind: Literal["source", "export", "preview"] = Form(...), change_note: str = Form(..., min_length=3, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Design asset not found")
    if asset.status not in {"draft", "rejected"}:
        raise HTTPException(status_code=409, detail="Additional files can only be added to draft or rejected assets")
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)
    storage_path = await design_asset_service.upload(file, size_bytes, asset.audience)
    db.add(DesignAssetVersion(asset_id=asset.id, revision=asset.revision, snapshot=_snapshot_asset(asset), change_note=change_note, changed_by=current_user.id))
    file_row = DesignAssetFile(asset_id=asset.id, file_kind=file_kind, provider=asset.provider, original_filename=file.filename or "design-asset", mime_type=file.content_type or "application/octet-stream", size_bytes=size_bytes, storage_path=storage_path, created_by=current_user.id)
    db.add(file_row)
    asset.revision += 1
    asset.status = "draft"
    asset.approved_by = None
    asset.approved_at = None
    asset.updated_by = current_user.id
    db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="file_added", details={"file_kind": file_kind, "revision": asset.revision, "note": change_note}))
    db.commit()
    return _asset_payload(db, asset)


@router.post("/assets/{asset_id}/revise", dependencies=[Depends(require_permission("design:write"))])
async def revise_design_asset(asset_id: UUID, request: AssetRevision, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Design asset not found")
    if asset.status not in {"draft", "rejected"}:
        raise HTTPException(status_code=409, detail="Only draft or rejected assets can be revised")
    db.add(DesignAssetVersion(asset_id=asset.id, revision=asset.revision, snapshot=_snapshot_asset(asset), change_note=request.change_note, changed_by=current_user.id))
    asset.title = request.title
    asset.usage_rights = request.usage_rights
    asset.revision += 1
    asset.status = "draft"
    asset.approved_by = None
    asset.approved_at = None
    asset.updated_by = current_user.id
    db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="revised", details={"revision": asset.revision, "note": request.change_note}))
    db.commit()
    return _asset_payload(db, asset)


@router.post("/assets/{asset_id}/submit", dependencies=[Depends(require_permission("design:write"))])
async def submit_design_asset(asset_id: UUID, note: str = Form(..., min_length=3, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Design asset not found")
    if asset.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft assets can be submitted for review")
    _brand_document(db, asset.brand_document_id, asset.brand_version, asset.audience)
    asset.status = "in_review"
    asset.updated_by = current_user.id
    db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="submitted_for_review", details={"note": note, "revision": asset.revision}))
    if asset.request_id:
        request_row = db.query(DesignRequest).filter(DesignRequest.id == asset.request_id).first()
        if request_row and request_row.status != "in_review":
            request_row.status = "in_review"
            db.add(DesignRequestEvent(request_id=request_row.id, actor_id=current_user.id, event_type="asset_submitted_for_review", details={"asset_id": str(asset.id)}))
    db.commit()
    return _asset_payload(db, asset)


async def _review_asset(asset_id: UUID, request: WorkflowReview, db: Session, current_user: Any, approve: bool):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Design asset not found")
    _validate_audience_access(db, current_user.id, asset.audience, action="review")
    if asset.status != "in_review":
        raise HTTPException(status_code=409, detail="Only in-review assets can be decided")
    if approve:
        _brand_document(db, asset.brand_document_id, asset.brand_version, asset.audience)
        if not request.source_verified or not asset.usage_rights.get("rights_basis") or not asset.usage_rights.get("permitted_uses"):
            raise HTTPException(status_code=422, detail="Approval requires verified brand guidance and documented usage rights")
        _validate_asset_usage_rights(asset)
        _validate_template_snapshot(db, asset)
        if asset.template_id:
            template = db.query(DesignTemplate).filter(DesignTemplate.id == asset.template_id).first()
            if not template or template.base_brand_version != asset.brand_version or template.base_brand_document_id != asset.brand_document_id:
                raise HTTPException(status_code=409, detail="The linked template or its brand version is no longer current and approved")
        asset.status = "approved"
        asset.approved_by = current_user.id
        asset.approved_at = datetime.now(timezone.utc)
    else:
        asset.status = "rejected"
        asset.approved_by = None
        asset.approved_at = None
    asset.updated_by = current_user.id
    db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="approved" if approve else "changes_requested", details={"note": request.note, "source_verified": request.source_verified if approve else False, "revision": asset.revision}))
    db.commit()
    return _asset_payload(db, asset)


@router.post("/assets/{asset_id}/approve-marketing", dependencies=[Depends(require_permission("design:review_marketing"))])
async def approve_marketing_asset(asset_id: UUID, request: WorkflowReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _review_asset(asset_id, request, db, current_user, True)


@router.post("/assets/{asset_id}/approve-programs", dependencies=[Depends(require_permission("design:review_programs"))])
async def approve_program_asset(asset_id: UUID, request: WorkflowReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _review_asset(asset_id, request, db, current_user, True)


@router.post("/assets/{asset_id}/request-changes-marketing", dependencies=[Depends(require_permission("design:review_marketing"))])
async def request_marketing_asset_changes(asset_id: UUID, request: WorkflowReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _review_asset(asset_id, request, db, current_user, False)


@router.post("/assets/{asset_id}/request-changes-programs", dependencies=[Depends(require_permission("design:review_programs"))])
async def request_program_asset_changes(asset_id: UUID, request: WorkflowReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _review_asset(asset_id, request, db, current_user, False)


async def _publish_asset(asset_id: UUID, db: Session, current_user: Any, audience: str):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Design asset not found")
    if asset.audience != audience and not (audience == "shared" and asset.audience == "shared"):
        raise HTTPException(status_code=403, detail="This publish permission does not cover the asset audience")
    if asset.audience == "shared" and not _has_scope(db, current_user.id, "design:manage"):
        raise HTTPException(status_code=403, detail="Only Designer owners and CEO can publish shared assets")
    if asset.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved assets can be published")
    _brand_document(db, asset.brand_document_id, asset.brand_version, asset.audience)
    _validate_asset_usage_rights(asset)
    _validate_template_snapshot(db, asset)
    if asset.template_id:
        template = db.query(DesignTemplate).filter(DesignTemplate.id == asset.template_id).first()
        if not template or template.base_brand_document_id != asset.brand_document_id or template.base_brand_version != asset.brand_version:
            raise HTTPException(status_code=409, detail="Template brand binding differs from the asset brand version")
    asset.status = "published"
    asset.published_by = current_user.id
    asset.published_at = datetime.now(timezone.utc)
    asset.updated_by = current_user.id
    db.add(DesignAssetEvent(asset_id=asset.id, actor_id=current_user.id, event_type="published", details={"audience": asset.audience, "revision": asset.revision, "external_publish": False}))
    if asset.request_id:
        request_row = db.query(DesignRequest).filter(DesignRequest.id == asset.request_id).first()
        if request_row:
            request_row.status = "completed"
            db.add(DesignRequestEvent(request_id=request_row.id, actor_id=current_user.id, event_type="completed", details={"asset_id": str(asset.id)}))
    db.commit()
    return _asset_payload(db, asset)


@router.post("/assets/{asset_id}/publish-marketing", dependencies=[Depends(require_permission("design:publish_marketing"))])
async def publish_marketing_asset(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _publish_asset(asset_id, db, current_user, "marketing")


@router.post("/assets/{asset_id}/publish-programs", dependencies=[Depends(require_permission("design:publish_programs"))])
async def publish_program_asset(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(DesignAsset).filter(DesignAsset.id == asset_id).first()
    if not asset or asset.audience not in {"programs", "student_success"}:
        raise HTTPException(status_code=403, detail="This publish permission does not cover the asset audience")
    return await _publish_asset(asset_id, db, current_user, asset.audience)


@router.post("/assets/{asset_id}/publish-shared", dependencies=[Depends(require_permission("design:publish"))])
async def publish_shared_asset(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _publish_asset(asset_id, db, current_user, "shared")


@router.get("/assets/{asset_id}/files/{file_id}/preview", dependencies=[Depends(require_permission("design:workspace"))])
async def get_design_asset_preview(asset_id: UUID, file_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = _visible_asset_query(db, current_user.id).filter(DesignAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Design asset not found")
    file_row = db.query(DesignAssetFile).filter(DesignAssetFile.id == file_id, DesignAssetFile.asset_id == asset_id).first()
    if not file_row:
        raise HTTPException(status_code=404, detail="Design asset file not found")
    signed_url = await design_asset_service.create_signed_url(file_row.storage_path)
    return {"signed_url": signed_url, "expires_in": 900, "mime_type": file_row.mime_type, "file_kind": file_row.file_kind}


@router.get("/assets/{asset_id}/history", dependencies=[Depends(require_permission("design:workspace"))])
async def get_design_asset_history(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = _visible_asset_query(db, current_user.id).filter(DesignAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Design asset not found")
    versions = db.query(DesignAssetVersion).filter(DesignAssetVersion.asset_id == asset_id).order_by(DesignAssetVersion.revision.desc()).all()
    events = db.query(DesignAssetEvent).filter(DesignAssetEvent.asset_id == asset_id).order_by(DesignAssetEvent.created_at.desc()).all()
    return {"versions": [{"revision": version.revision, "snapshot": version.snapshot, "change_note": version.change_note, "changed_by": str(version.changed_by), "created_at": version.created_at.isoformat() if version.created_at else None} for version in versions], "events": [{"event_type": event.event_type, "details": event.details, "actor_id": str(event.actor_id), "created_at": event.created_at.isoformat() if event.created_at else None} for event in events]}
