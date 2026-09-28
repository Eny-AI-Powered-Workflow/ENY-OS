# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/graphic_designer.py

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.design_system import DesignSystemDocument, DesignSystemDocumentEvent, DesignSystemDocumentVersion
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole

router = APIRouter()
Audience = Literal["shared", "marketing", "programs", "student_success"]


class DesignDocumentCreate(BaseModel):
    document_key: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9][a-z0-9._-]+$")
    title: str = Field(..., min_length=3, max_length=240)
    category: str = Field(..., min_length=2, max_length=80)
    audience: Audience
    content: str = Field(..., min_length=1, max_length=50000)
    source_reference: Optional[str] = Field(None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DesignDocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=240)
    category: Optional[str] = Field(None, min_length=2, max_length=80)
    audience: Optional[Audience] = None
    content: Optional[str] = Field(None, min_length=1, max_length=50000)
    source_reference: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[dict[str, Any]] = None
    change_note: str = Field(..., min_length=3, max_length=1000)


class DesignDocumentReview(BaseModel):
    approval_note: str = Field(..., min_length=5, max_length=2000)
    source_verified: bool


class DesignDocumentChangesRequest(BaseModel):
    note: str = Field(..., min_length=3, max_length=1000)


def _has_scope(db: Session, user_id: UUID, scope: str) -> bool:
    return db.query(Permission.id).join(RolePermission, Permission.id == RolePermission.permission_id).join(
        UserRole, RolePermission.role_id == UserRole.role_id
    ).filter(UserRole.user_id == user_id, Permission.scope == scope).first() is not None


def _serialize(document: DesignSystemDocument) -> dict[str, Any]:
    return {
        "id": str(document.id),
        "document_key": document.document_key,
        "title": document.title,
        "category": document.category,
        "audience": document.audience,
        "status": document.status,
        "source_status": document.source_status,
        "source_reference": document.source_reference,
        "content": document.content,
        "metadata": document.metadata_json or {},
        "version": document.version,
        "approved_by": str(document.approved_by) if document.approved_by else None,
        "approved_at": document.approved_at.isoformat() if document.approved_at else None,
        "authoritative": document.status == "approved" and document.source_status == "verified",
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
    }


def _visible_document_query(db: Session, user_id: UUID):
    if _has_scope(db, user_id, "design:manage"):
        return db.query(DesignSystemDocument)
    audience_filters = []
    if _has_scope(db, user_id, "design:read_marketing"):
        audience_filters.append((DesignSystemDocument.audience.in_(["marketing", "shared"])) & (DesignSystemDocument.status == "approved"))
    if _has_scope(db, user_id, "design:review_marketing"):
        audience_filters.append((DesignSystemDocument.audience.in_(["marketing", "shared"])) & (DesignSystemDocument.status == "in_review"))
    if _has_scope(db, user_id, "design:read_programs"):
        audience_filters.append((DesignSystemDocument.audience.in_(["programs", "student_success", "shared"])) & (DesignSystemDocument.status == "approved"))
    if _has_scope(db, user_id, "design:review_programs"):
        audience_filters.append((DesignSystemDocument.audience.in_(["programs", "student_success", "shared"])) & (DesignSystemDocument.status == "in_review"))
    if not audience_filters:
        raise HTTPException(status_code=403, detail="No Designer documents are available to this account")
    return db.query(DesignSystemDocument).filter(or_(*audience_filters))


def _snapshot(document: DesignSystemDocument) -> dict[str, Any]:
    return {
        "document_key": document.document_key,
        "title": document.title,
        "category": document.category,
        "audience": document.audience,
        "status": document.status,
        "source_status": document.source_status,
        "source_reference": document.source_reference,
        "content": document.content,
        "metadata": document.metadata_json or {},
        "version": document.version,
    }


@router.get("/foundation", dependencies=[Depends(require_permission("design:workspace"))])
async def list_design_foundation(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    documents = _visible_document_query(db, current_user.id).order_by(DesignSystemDocument.audience, DesignSystemDocument.category, DesignSystemDocument.title).limit(500).all()
    scopes = [scope for scope in ("design:manage", "design:write", "design:read_marketing", "design:read_programs", "design:review_marketing", "design:review_programs", "design:templates", "design:funnels", "design:analytics", "design:publish") if _has_scope(db, current_user.id, scope)]
    return {"documents": [_serialize(document) for document in documents], "permissions": scopes}


@router.get("/foundation/authoritative", dependencies=[Depends(require_permission("design:workspace"))])
async def list_authoritative_design_knowledge(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    visible = _visible_document_query(db, current_user.id)
    documents = visible.filter(DesignSystemDocument.status == "approved", DesignSystemDocument.source_status == "verified").order_by(DesignSystemDocument.audience, DesignSystemDocument.category, DesignSystemDocument.title).all()
    return {"documents": [_serialize(document) for document in documents]}


@router.post("/foundation", dependencies=[Depends(require_permission("design:write"))])
async def create_design_foundation_document(request: DesignDocumentCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    existing = db.query(DesignSystemDocument.id).filter(DesignSystemDocument.document_key == request.document_key, DesignSystemDocument.audience == request.audience).first()
    if existing:
        raise HTTPException(status_code=409, detail="A document with this key already exists for the selected audience")
    document = DesignSystemDocument(
        document_key=request.document_key,
        title=request.title,
        category=request.category,
        audience=request.audience,
        content=request.content,
        source_status="unverified",
        source_reference=request.source_reference,
        metadata_json=request.metadata,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(document)
    db.flush()
    db.add(DesignSystemDocumentEvent(document_id=document.id, actor_id=current_user.id, event_type="created", details={"audience": document.audience, "source_status": document.source_status}))
    db.commit()
    return _serialize(document)


@router.patch("/foundation/{document_id}", dependencies=[Depends(require_permission("design:write"))])
async def update_design_foundation_document(document_id: UUID, request: DesignDocumentUpdate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    document = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Design foundation document not found")
    if document.status not in {"draft", "in_review"}:
        raise HTTPException(status_code=409, detail="Approved or archived guidance cannot be edited; create a new version from a draft")
    values = request.model_dump(exclude_unset=True, exclude={"change_note"})
    next_audience = values.get("audience", document.audience)
    next_key = values.get("document_key", document.document_key)
    duplicate = db.query(DesignSystemDocument.id).filter(
        DesignSystemDocument.document_key == next_key,
        DesignSystemDocument.audience == next_audience,
        DesignSystemDocument.id != document.id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A document with this key already exists for the selected audience")
    db.add(DesignSystemDocumentVersion(document_id=document.id, version=document.version, snapshot=_snapshot(document), change_note=request.change_note, changed_by=current_user.id))
    for key, value in values.items():
        if key == "metadata":
            document.metadata_json = value or {}
        else:
            setattr(document, key, value)
    document.version += 1
    document.status = "draft"
    document.source_status = "unverified"
    document.approved_by = None
    document.approved_at = None
    document.updated_by = current_user.id
    db.add(DesignSystemDocumentEvent(document_id=document.id, actor_id=current_user.id, event_type="edited", details={"version": document.version, "note": request.change_note}))
    db.commit()
    return _serialize(document)


@router.post("/foundation/{document_id}/submit", dependencies=[Depends(require_permission("design:write"))])
async def submit_design_document_for_review(document_id: UUID, note: str = Query(..., min_length=3, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    document = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Design foundation document not found")
    if document.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft foundation documents can be submitted")
    document.status = "in_review"
    document.updated_by = current_user.id
    db.add(DesignSystemDocumentEvent(document_id=document.id, actor_id=current_user.id, event_type="submitted_for_review", details={"note": note, "source_status": document.source_status}))
    db.commit()
    return _serialize(document)


async def _approve_design_document(document_id: UUID, request: DesignDocumentReview, db: Session, current_user: Any, audience_group: set[str]):
    document = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Design foundation document not found")
    allowed_audiences = audience_group | {"shared"}
    if document.audience not in allowed_audiences:
        raise HTTPException(status_code=403, detail="This reviewer cannot approve the selected audience")
    if document.status != "in_review":
        raise HTTPException(status_code=409, detail="Only documents in review can be approved")
    if not request.source_verified or not (document.source_reference or "").strip():
        raise HTTPException(status_code=422, detail="Approval requires a source reference and explicit source verification")
    document.status = "approved"
    document.source_status = "verified"
    document.approved_by = current_user.id
    document.approved_at = datetime.now(timezone.utc)
    document.updated_by = current_user.id
    db.add(DesignSystemDocumentEvent(document_id=document.id, actor_id=current_user.id, event_type="approved", details={"approval_note": request.approval_note, "source_verified": True, "version": document.version, "audience": document.audience}))
    db.commit()
    return _serialize(document)


@router.post("/foundation/{document_id}/approve-marketing", dependencies=[Depends(require_permission("design:review_marketing"))])
async def approve_marketing_design_document(document_id: UUID, request: DesignDocumentReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _approve_design_document(document_id, request, db, current_user, {"marketing"})


@router.post("/foundation/{document_id}/approve-programs", dependencies=[Depends(require_permission("design:review_programs"))])
async def approve_program_design_document(document_id: UUID, request: DesignDocumentReview, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _approve_design_document(document_id, request, db, current_user, {"programs", "student_success"})


async def _request_design_changes(document_id: UUID, request: DesignDocumentChangesRequest, db: Session, current_user: Any, audience_group: set[str]):
    document = db.query(DesignSystemDocument).filter(DesignSystemDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Design foundation document not found")
    if document.audience not in audience_group | {"shared"}:
        raise HTTPException(status_code=403, detail="This reviewer cannot return the selected audience's document")
    if document.status != "in_review":
        raise HTTPException(status_code=409, detail="Only documents in review can be returned for changes")
    document.status = "draft"
    document.updated_by = current_user.id
    db.add(DesignSystemDocumentEvent(document_id=document.id, actor_id=current_user.id, event_type="changes_requested", details={"note": request.note, "audience": document.audience}))
    db.commit()
    return _serialize(document)


@router.post("/foundation/{document_id}/request-marketing-changes", dependencies=[Depends(require_permission("design:review_marketing"))])
async def request_marketing_design_changes(document_id: UUID, request: DesignDocumentChangesRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _request_design_changes(document_id, request, db, current_user, {"marketing"})


@router.post("/foundation/{document_id}/request-program-changes", dependencies=[Depends(require_permission("design:review_programs"))])
async def request_program_design_changes(document_id: UUID, request: DesignDocumentChangesRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _request_design_changes(document_id, request, db, current_user, {"programs", "student_success"})


@router.get("/foundation/{document_id}/history", dependencies=[Depends(require_permission("design:workspace"))])
async def get_design_document_history(document_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    visible = _visible_document_query(db, current_user.id).filter(DesignSystemDocument.id == document_id).first()
    if not visible:
        raise HTTPException(status_code=404, detail="Design foundation document not found")
    versions = db.query(DesignSystemDocumentVersion).filter(DesignSystemDocumentVersion.document_id == document_id).order_by(DesignSystemDocumentVersion.version.desc()).all()
    events = db.query(DesignSystemDocumentEvent).filter(DesignSystemDocumentEvent.document_id == document_id).order_by(DesignSystemDocumentEvent.created_at.desc()).all()
    return {
        "versions": [{"version": item.version, "snapshot": item.snapshot, "change_note": item.change_note, "changed_by": str(item.changed_by), "created_at": item.created_at.isoformat() if item.created_at else None} for item in versions],
        "events": [{"event_type": item.event_type, "details": item.details, "actor_id": str(item.actor_id), "created_at": item.created_at.isoformat() if item.created_at else None} for item in events],
    }
