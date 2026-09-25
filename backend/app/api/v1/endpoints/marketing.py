# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/marketing.py
from datetime import datetime, timezone
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Literal, Optional
from app.api.deps import require_permission
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.services.ghl_service import ghl_service
from app.services.claude_service import ClaudeService
from app.services.knowledge_service import retrieve_knowledge
from app.models.marketing_content import MarketingContentEvent, MarketingContentItem
from app.models.marketing_delivery import MarketingDelivery, MarketingDeliveryEvent
from app.models.operational_alert import OperationalAlert
from app.services.marketing_delivery_service import marketing_delivery_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

CONTENT_TYPES = {"social_post", "email_campaign", "blog_article", "video_script", "short_form_caption", "repurposed_content", "seo_brief"}
CHANNELS = {"linkedin", "instagram", "facebook", "x", "tiktok", "email", "blog"}


class ContentStatusRequest(BaseModel):
    status: Literal["draft", "in_review", "revision_required", "approved", "scheduled", "published", "rejected"]
    note: str = Field(..., min_length=3, max_length=1000)


class ContentCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=240)
    content_type: str
    channel: str
    content: str = Field(..., min_length=1, max_length=50000)
    due_at: Optional[datetime] = None
    prompt: Optional[str] = Field(None, max_length=10000)
    source_documents: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str = "unverified"


class DeliveryScheduleRequest(BaseModel):
    content_id: UUID
    channel: Literal["email", "linkedin", "instagram", "facebook", "x", "tiktok"]
    scheduled_at: datetime
    recipients: list[dict[str, str]] = Field(default_factory=list)
    subject: Optional[str] = Field(None, max_length=240)
    unsubscribe_url: Optional[str] = Field(None, max_length=2000)
    consent_confirmed: bool = False
    sensitive_broadcast: bool = False
    ceo_approval_note: Optional[str] = Field(None, max_length=1000)

@router.get("/metrics", dependencies=[Depends(require_permission("marketing:analytics"))])
async def get_marketing_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get marketing dashboard metrics.
    Requires marketing:analytics permission.
    """
    try:
        contacts, _ = await ghl_service.get_all_contacts()
        pipeline = await ghl_service.get_pipeline_data()
        current_month = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m")
        metrics = {
            "totalLeads": len(contacts),
            "leadsThisMonth": sum(1 for contact in contacts if str(contact.get("dateAdded", "")).startswith(current_month)),
            "conversionRate": round(float(pipeline.get("conversion_rate", 0)) * 100, 2),
            "roi": None,
        }
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching marketing metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )

@router.get("/analytics", dependencies=[Depends(require_permission("marketing:analytics"))])
async def get_marketing_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get marketing analytics.
    Requires marketing:analytics permission.
    """
    try:
        campaigns = [
            {
                "id": "1",
                "name": "Q3 Social Media Campaign",
                "description": "Facebook and Instagram lead generation campaign",
                "impressions": 125000,
                "clicks": 3200,
                "ctr": 2.56,
                "conversions": 185,
                "conversionRate": 5.78,
                "cost": 8500,
                "roi": 4.2
            },
            {
                "id": "2",
                "name": "Email Newsletter Series",
                "description": "Monthly educational newsletter",
                "impressions": 89000,
                "clicks": 4500,
                "ctr": 5.06,
                "conversions": 210,
                "conversionRate": 4.67,
                "cost": 3200,
                "roi": 8.9
            }
        ]
        return {"campaigns": campaigns}
    except Exception as e:
        logger.error(f"Error fetching marketing analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analytics: {str(e)}"
        )


def _serialize_content(item: MarketingContentItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "title": item.title,
        "content_type": item.content_type,
        "channel": item.channel,
        "status": item.status,
        "content": item.content,
        "campaign_owner_id": str(item.campaign_owner_id) if item.campaign_owner_id else None,
        "due_at": item.due_at.isoformat() if item.due_at else None,
        "prompt": item.prompt,
        "source_documents": item.source_documents,
        "confidence": item.confidence,
        "revision": item.revision,
        "approval_required": item.approval_required,
        "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.get("/content", dependencies=[Depends(require_permission("marketing:read"))])
async def list_marketing_content(
    status_filter: Optional[str] = Query(None, alias="status"),
    channel: Optional[str] = None,
    content_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    query = db.query(MarketingContentItem)
    if status_filter:
        query = query.filter(MarketingContentItem.status == status_filter)
    if channel:
        query = query.filter(MarketingContentItem.channel == channel)
    if content_type:
        query = query.filter(MarketingContentItem.content_type == content_type)
    items = query.order_by(MarketingContentItem.due_at.asc().nullslast(), MarketingContentItem.created_at.desc()).limit(300).all()
    return {"items": [_serialize_content(item) for item in items]}


@router.post("/content", dependencies=[Depends(require_permission("marketing:write"))])
async def create_marketing_content(
    request: ContentCreateRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    if request.content_type not in CONTENT_TYPES or request.channel not in CHANNELS:
        raise HTTPException(status_code=422, detail="Unsupported Marketing content type or channel")
    item = MarketingContentItem(
        title=request.title,
        content_type=request.content_type,
        channel=request.channel,
        content=request.content,
        due_at=request.due_at,
        prompt=request.prompt,
        source_documents=request.source_documents,
        confidence=request.confidence,
        created_by=current_user.id,
        campaign_owner_id=current_user.id,
    )
    db.add(item)
    db.flush()
    db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="created", details={"status": item.status}))
    db.commit()
    return _serialize_content(item)


@router.patch("/content/{content_id}/status", dependencies=[Depends(require_permission("marketing:approve"))])
async def update_marketing_content_status(
    content_id: UUID,
    request: ContentStatusRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    item = db.query(MarketingContentItem).filter(MarketingContentItem.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Marketing content not found")
    if request.status == "published":
        raise HTTPException(status_code=409, detail="Use the publish endpoint with marketing:publish permission")
    if request.status in {"scheduled", "published"} and item.status != "approved":
        raise HTTPException(status_code=409, detail="Content must be approved before scheduling or publishing")
    previous_status = item.status
    item.status = request.status
    if request.status == "approved":
        item.approved_by = current_user.id
        item.approved_at = datetime.now(timezone.utc)
    db.add(MarketingContentEvent(
        content_id=item.id,
        actor_id=current_user.id,
        event_type="status_changed",
        details={"from": previous_status, "to": request.status, "note": request.note},
    ))
    db.commit()
    return _serialize_content(item)


@router.patch("/content/{content_id}/publish", dependencies=[Depends(require_permission("marketing:publish"))])
async def publish_marketing_content(
    content_id: UUID,
    request: ContentStatusRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    item = db.query(MarketingContentItem).filter(MarketingContentItem.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Marketing content not found")
    if item.status != "approved":
        raise HTTPException(status_code=409, detail="Content must be approved before publishing")
    item.status = "published"
    db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="published", details={"note": request.note, "external_publish": False}))
    db.commit()
    return _serialize_content(item)


@router.get("/deliveries", dependencies=[Depends(require_permission("marketing:read"))])
async def list_marketing_deliveries(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    deliveries = db.query(MarketingDelivery).order_by(MarketingDelivery.scheduled_at.desc()).limit(200).all()
    return {"deliveries": [
        {
            "id": str(delivery.id),
            "content_id": str(delivery.content_id),
            "channel": delivery.channel,
            "provider": delivery.provider,
            "status": delivery.status,
            "scheduled_at": delivery.scheduled_at.isoformat(),
            "sent_at": delivery.sent_at.isoformat() if delivery.sent_at else None,
            "recipient_count": delivery.recipient_count,
            "metrics": delivery.metrics,
            "error": delivery.error,
        }
        for delivery in deliveries
    ]}


@router.post("/deliveries/schedule", dependencies=[Depends(require_permission("marketing:send"))])
async def schedule_marketing_delivery(
    request: DeliveryScheduleRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    content = db.query(MarketingContentItem).filter(MarketingContentItem.id == request.content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Marketing content not found")
    if content.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved content can be scheduled")
    if request.sensitive_broadcast:
        raise HTTPException(status_code=409, detail="Use the CEO-only sensitive scheduling endpoint")
    if request.channel == "email" and (not request.consent_confirmed or not request.unsubscribe_url or not request.subject):
        raise HTTPException(status_code=422, detail="Email requires consent confirmation, subject, and unsubscribe URL")
    provider = "ghl" if request.channel == "email" else "buffer"
    delivery = MarketingDelivery(
        content_id=content.id,
        channel=request.channel,
        provider=provider,
        status="scheduled",
        scheduled_at=request.scheduled_at,
        recipient_count=len(request.recipients),
        details={"recipients": request.recipients, "subject": request.subject, "unsubscribe_url": request.unsubscribe_url, "sensitive_broadcast": bool(request.ceo_approval_note), "ceo_approval_note": request.ceo_approval_note},
        created_by=current_user.id,
    )
    db.add(delivery)
    db.flush()
    db.add(MarketingDeliveryEvent(delivery_id=delivery.id, actor_id=current_user.id, event_type="scheduled", details={"provider": provider}))
    db.commit()
    return {"id": str(delivery.id), "status": delivery.status, "provider": provider}


@router.post("/deliveries/schedule-sensitive", dependencies=[Depends(require_permission("marketing:send")), Depends(require_permission("marketing:approve_sensitive"))])
async def schedule_sensitive_marketing_delivery(
    request: DeliveryScheduleRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    request.sensitive_broadcast = True
    if not request.ceo_approval_note:
        raise HTTPException(status_code=422, detail="CEO approval note is required")
    request.sensitive_broadcast = False
    return await schedule_marketing_delivery(request=request, db=db, current_user=current_user)


@router.post("/deliveries/{delivery_id}/execute", dependencies=[Depends(require_permission("marketing:send"))])
async def execute_marketing_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    delivery = db.query(MarketingDelivery).filter(MarketingDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Marketing delivery not found")
    content = db.query(MarketingContentItem).filter(MarketingContentItem.id == delivery.content_id).first()
    if not content or content.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved content can be delivered")
    details = delivery.details or {}
    if delivery.provider == "ghl":
        result = await marketing_delivery_service.send_ghl_email(
            details.get("recipients", []),
            details.get("subject") or content.title,
            content.content,
            details.get("unsubscribe_url") or "https://enyconsulting.com/unsubscribe",
        )
        success = result.get("status") == "sent"
    else:
        profile_ids = [value.strip() for value in settings.BUFFER_PROFILE_IDS.split(",") if value.strip()]
        result = await marketing_delivery_service.schedule_buffer(content.content, profile_ids, delivery.scheduled_at)
        success = result.get("status") == "scheduled"
    delivery.status = "sent" if success else "failed"
    delivery.sent_at = datetime.now(timezone.utc) if success else None
    delivery.metrics = result
    delivery.error = None if success else "; ".join(result.get("errors", []))
    db.add(MarketingDeliveryEvent(delivery_id=delivery.id, actor_id=current_user.id, event_type="sent" if success else "failed", details=result))
    if not success:
        db.add(OperationalAlert(
            team="marketing",
            alert_type="marketing_delivery_failure",
            severity="critical",
            source=delivery.provider,
            message="Approved Marketing content delivery failed.",
            details={"delivery_id": str(delivery.id), "result": result},
        ))
    db.commit()
    if not success:
        raise HTTPException(status_code=502, detail={"message": "Marketing delivery failed", "result": result})
    return {"id": str(delivery.id), "status": delivery.status, "metrics": result}


@router.get("/content/{content_id}/history", dependencies=[Depends(require_permission("marketing:read"))])
async def get_marketing_content_history(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    events = db.query(MarketingContentEvent).filter(MarketingContentEvent.content_id == content_id).order_by(MarketingContentEvent.created_at.desc()).all()
    return {"events": [{"id": str(event.id), "event_type": event.event_type, "details": event.details, "created_at": event.created_at.isoformat() if event.created_at else None} for event in events]}


@router.post("/content/generate-weekly", dependencies=[Depends(require_permission("marketing:write"))])
async def generate_weekly_marketing_content(
    topic: str = Query(..., min_length=3, max_length=500),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Generate a reviewable weekly content plan using Marketing-scoped knowledge."""
    knowledge = await retrieve_knowledge(db, ["marketing"], topic, limit=8)
    source_documents = [{"title": entry.get("title"), "source": entry.get("source"), "similarity": entry.get("similarity")} for entry in knowledge]
    prompt = f"""Create a weekly ENY Marketing content plan about: {topic}
Return JSON with an items array. Create 5-7 social posts per platform for LinkedIn, Instagram, Facebook, X, and TikTok; 2-3 email campaign drafts; one blog article; one video script; and one SEO brief. Keep each item concise but useful. Use only the approved Marketing knowledge context below for factual claims. Mark unsupported claims as needing review.
Approved Marketing knowledge context:
{json.dumps(knowledge, default=str)}
Each item must include title, content_type, channel, content, confidence, and due_day."""
    response = await ClaudeService().invoke(prompt=prompt, role_context="marketing", max_tokens=7000, temperature=0.7)
    try:
        generated = json.loads(response)
        generated_items = generated.get("items", []) if isinstance(generated, dict) else []
    except json.JSONDecodeError:
        generated_items = [{"title": f"Marketing draft: {topic}", "content_type": "social_post", "channel": "linkedin", "content": response, "confidence": "unverified", "due_day": 1}]
    created = []
    for generated_item in generated_items:
        if generated_item.get("content_type") not in CONTENT_TYPES or generated_item.get("channel") not in CHANNELS:
            continue
        item = MarketingContentItem(
            title=str(generated_item.get("title") or f"{topic} draft"),
            content_type=generated_item["content_type"],
            channel=generated_item["channel"],
            content=str(generated_item.get("content") or ""),
            prompt=prompt,
            source_documents=source_documents,
            confidence=str(generated_item.get("confidence") or "unverified"),
            created_by=current_user.id,
            campaign_owner_id=current_user.id,
        )
        db.add(item)
        db.flush()
        db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="generated", details={"topic": topic, "source_count": len(source_documents)}))
        created.append(item)
    db.commit()
    return {"status": "generated", "count": len(created), "items": [_serialize_content(item) for item in created], "source_documents": source_documents}