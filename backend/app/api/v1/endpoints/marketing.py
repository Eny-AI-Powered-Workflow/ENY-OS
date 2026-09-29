# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/marketing.py
from datetime import date, datetime, timedelta, timezone
import json
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Literal, Optional
from urllib.parse import urlsplit
from app.api.deps import require_any_permission, require_permission
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.services.ghl_service import ghl_service
from app.services.claude_service import ClaudeService
from app.services.knowledge_service import retrieve_knowledge
from app.models.marketing_content import MarketingContentEvent, MarketingContentItem, MarketingContentVersion, MarketingWeeklyReview
from app.models.marketing_delivery import MarketingDelivery, MarketingDeliveryEvent
from app.models.operational_alert import OperationalAlert
from app.models.marketing_intelligence import MarketingIntelligenceEvent, MarketingMetricObservation, MarketingSeoObservation, MarketingSocialMention, MarketingVideoAsset
from app.services.marketing_delivery_service import marketing_delivery_service
from app.services.marketing_intelligence_service import marketing_intelligence_service
from app.services.marketing_video_service import marketing_video_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

CONTENT_TYPES = {"social_post", "email_campaign", "blog_article", "video_script", "short_form_caption", "repurposed_content", "seo_brief"}
CHANNELS = {"linkedin", "instagram", "facebook", "x", "tiktok", "email", "blog"}
SEO_OBSERVATION_TYPES = {"keyword", "ranking", "search_performance", "content_opportunity", "competitor", "technical_issue", "ai_overview"}
SOCIAL_CLASSIFICATIONS = {"lead", "opportunity", "customer_question", "positive_mention", "complaint", "spam", "unclassified"}
SOCIAL_SENTIMENTS = {"positive", "neutral", "negative", "mixed", "unclassified"}
SOCIAL_RISK_LEVELS = {"low", "medium", "high", "critical"}
CAMPAIGN_METRICS = {
    "email_delivery_rate", "email_open_rate", "email_click_rate", "email_unsubscribe_rate",
    "social_reach", "social_engagement", "website_sessions", "content_assisted_conversions",
    "ghl_pipeline_value", "spend", "attributed_revenue",
}


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


class ContentUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=240)
    content_type: Optional[str] = None
    channel: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1, max_length=50000)
    due_at: Optional[datetime] = None
    source_documents: Optional[list[dict[str, Any]]] = None
    note: str = Field(..., min_length=3, max_length=1000)


class SensitiveApprovalRequest(BaseModel):
    approval_note: str = Field(..., min_length=10, max_length=2000)
    claims_verified: bool


class WeeklyReviewRequest(BaseModel):
    week_start: date
    summary: str = Field(..., min_length=10, max_length=10000)
    decisions: list[str] = Field(default_factory=list, max_length=50)
    attendees: list[str] = Field(default_factory=list, max_length=50)


class IntegrationHealthRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=120)
    status: Literal["connected", "error"]
    observed_at: datetime
    message: Optional[str] = Field(None, max_length=1000)


class BrandReviewRequest(BaseModel):
    note: str = Field("Routine brand and SOP review", min_length=3, max_length=1000)


class DeliveryScheduleRequest(BaseModel):
    content_id: UUID
    channel: Literal["email", "linkedin", "instagram", "facebook", "x", "tiktok"]
    scheduled_at: datetime
    recipients: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    subject: Optional[str] = Field(None, max_length=240)
    unsubscribe_url: Optional[str] = Field(None, max_length=2000)
    consent_confirmed: bool = False
    consent_evidence: Optional[str] = Field(None, min_length=5, max_length=500)
    sensitive_broadcast: bool = False
    ceo_approval_note: Optional[str] = Field(None, max_length=1000)


class SeoObservationRequest(BaseModel):
    observation_type: Literal["keyword", "ranking", "search_performance", "content_opportunity", "competitor", "technical_issue", "ai_overview"]
    keyword: Optional[str] = Field(None, max_length=500)
    url: Optional[str] = Field(None, max_length=2000)
    value: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(..., min_length=2, max_length=120)
    observed_at: datetime


class SocialMentionRequest(BaseModel):
    platform: str = Field(..., min_length=2, max_length=50)
    external_id: Optional[str] = Field(None, max_length=240)
    author: Optional[str] = Field(None, max_length=240)
    text: str = Field(..., min_length=1, max_length=10000)
    url: Optional[str] = Field(None, max_length=2000)
    matched_term: str = Field(..., min_length=2, max_length=240)
    classification: Literal["lead", "opportunity", "customer_question", "positive_mention", "complaint", "spam", "unclassified"] = "unclassified"
    sentiment: Literal["positive", "neutral", "negative", "mixed", "unclassified"] = "unclassified"
    risk_level: Literal["low", "medium", "high", "critical"] = "low"
    observed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class CampaignMetricRequest(BaseModel):
    metric_key: Literal["email_delivery_rate", "email_open_rate", "email_click_rate", "email_unsubscribe_rate", "social_reach", "social_engagement", "website_sessions", "content_assisted_conversions", "ghl_pipeline_value", "spend", "attributed_revenue"]
    metric_value: float = Field(..., ge=0)
    campaign_name: Optional[str] = Field(None, max_length=240)
    channel: Optional[str] = Field(None, max_length=80)
    provider: str = Field(..., min_length=2, max_length=120)
    source: str = Field(..., min_length=2, max_length=500)
    observed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


def _source_status(family: str) -> dict[str, Any]:
    providers = marketing_intelligence_service.provider_status()
    configured = marketing_intelligence_service.configured_sources(family)
    return {"status": "configured" if configured else "not_configured", "configured_sources": configured, "providers": providers}


SENSITIVE_CLAIM_PATTERNS = {
    "health": re.compile(r"\b(cure|treat|heal|diagnos|medical|health outcome|clinically proven)\w*\b", re.IGNORECASE),
    "income": re.compile(r"\b(earn|income|salary|make money|profit|revenue|guaranteed returns?)\b", re.IGNORECASE),
    "legal": re.compile(r"\b(legal advice|legally compliant|guaranteed compliance|lawful in every)\b", re.IGNORECASE),
    "financial": re.compile(r"\b(investment advice|financial advice|risk-free|guaranteed roi|guaranteed return)\b", re.IGNORECASE),
    "quantified_performance": re.compile(r"(?:\b\d+(?:\.\d+)?\s?%|\$\s?\d|\b\d+(?:\.\d+)?x\b|\b\d+\s+(?:clients|students|customers|companies|businesses)\b)", re.IGNORECASE),
    "announcement_or_major_campaign": re.compile(r"\b(official announcement|public announcement|company-wide announcement|product launch|major campaign)\b", re.IGNORECASE),
}


def _sensitive_claim_flags(content: str) -> list[str]:
    return [category for category, pattern in SENSITIVE_CLAIM_PATTERNS.items() if pattern.search(content)]


def _apply_sensitive_claim_policy(item: MarketingContentItem) -> None:
    item.compliance_flags = _sensitive_claim_flags(item.content)
    item.requires_ceo_approval = bool(item.compliance_flags)


def _content_snapshot(item: MarketingContentItem) -> dict[str, Any]:
    return {
        "title": item.title,
        "content_type": item.content_type,
        "channel": item.channel,
        "content": item.content,
        "due_at": item.due_at.isoformat() if item.due_at else None,
        "source_documents": item.source_documents,
        "confidence": item.confidence,
        "status": item.status,
        "revision": item.revision,
    }


def _raise_marketing_alert(
    db: Session,
    alert_type: str,
    source: str,
    message: str,
    details: dict[str, Any],
    severity: str = "warning",
) -> None:
    existing = db.query(OperationalAlert).filter(
        OperationalAlert.team == "marketing",
        OperationalAlert.alert_type == alert_type,
        OperationalAlert.source == source,
        OperationalAlert.status == "open",
    ).first()
    if existing:
        existing.details = {**(existing.details or {}), **details}
        existing.message = message
        return
    db.add(OperationalAlert(team="marketing", alert_type=alert_type, severity=severity, source=source, message=message, details=details))


def _build_marketing_weekly_report(db: Session, now: datetime) -> dict[str, Any]:
    week_start = now - timedelta(days=7)
    content = db.query(MarketingContentItem).filter(MarketingContentItem.created_at >= week_start).all()
    events = db.query(MarketingContentEvent).filter(MarketingContentEvent.created_at >= week_start).order_by(MarketingContentEvent.created_at.asc()).all()
    review_started: dict[UUID, datetime] = {}
    approval_durations: list[float] = []
    scheduled_content: set[UUID] = set()
    published_content: set[UUID] = set()
    brand_checks: list[dict[str, Any]] = []
    for event in events:
        details = event.details or {}
        if event.event_type == "submitted_for_review" or (event.event_type == "status_changed" and details.get("to") == "in_review"):
            review_started[event.content_id] = event.created_at
        if event.event_type == "status_changed" and details.get("to") == "approved" or event.event_type == "sensitive_approved":
            submitted_at = review_started.get(event.content_id)
            if submitted_at and event.created_at >= submitted_at:
                approval_durations.append((event.created_at - submitted_at).total_seconds() / 3600)
        if event.event_type == "scheduled":
            scheduled_content.add(event.content_id)
        if event.event_type == "published":
            published_content.add(event.content_id)
        if event.event_type == "brand_compliance_review":
            brand_checks.append(details)

    created_count = len(content)
    revised_count = db.query(MarketingContentVersion).filter(MarketingContentVersion.created_at >= week_start).count()
    pending = db.query(MarketingContentItem).filter(MarketingContentItem.status == "in_review").all()
    pending_ids = [item.id for item in pending]
    review_events = db.query(MarketingContentEvent).filter(MarketingContentEvent.content_id.in_(pending_ids)).order_by(MarketingContentEvent.created_at.desc()).all() if pending_ids else []
    latest_submission: dict[UUID, datetime] = {}
    for event in review_events:
        if event.event_type == "submitted_for_review" or (event.event_type == "status_changed" and (event.details or {}).get("to") == "in_review"):
            latest_submission.setdefault(event.content_id, event.created_at)
    overdue = [item for item in pending if latest_submission.get(item.id) and latest_submission[item.id] < now - timedelta(hours=settings.MARKETING_APPROVAL_SLA_HOURS)]

    seo_observations = db.query(MarketingSeoObservation).filter(MarketingSeoObservation.observed_at >= week_start - timedelta(days=7)).order_by(MarketingSeoObservation.observed_at.desc()).limit(1000).all()
    rankings_by_keyword: dict[str, list[MarketingSeoObservation]] = {}
    for observation in seo_observations:
        if observation.observation_type == "ranking" and observation.keyword:
            rankings_by_keyword.setdefault(observation.keyword, []).append(observation)
    seo_movement = []
    for keyword, observations in rankings_by_keyword.items():
        positions = [item for item in observations if isinstance(item.value, dict) and isinstance(item.value.get("position"), (int, float))]
        if len(positions) >= 2:
            latest, previous = positions[0], positions[1]
            seo_movement.append({"keyword": keyword, "previous_position": previous.value["position"], "latest_position": latest.value["position"], "change": round(float(previous.value["position"]) - float(latest.value["position"]), 2), "source": latest.source, "observed_at": latest.observed_at.isoformat()})

    metrics = db.query(MarketingMetricObservation).filter(MarketingMetricObservation.observed_at >= week_start - timedelta(days=30)).order_by(MarketingMetricObservation.observed_at.desc()).limit(2000).all()
    latest_metric_values: dict[tuple[str, Optional[str]], list[MarketingMetricObservation]] = {}
    for metric in metrics:
        latest_metric_values.setdefault((metric.metric_key, metric.campaign_name), []).append(metric)
    engagement = [metric for (key, _), items in latest_metric_values.items() if key == "social_engagement" for metric in items[:1]]
    email_performance = {key: [{"campaign": item.campaign_name, "value": float(item.metric_value), "source": item.source, "observed_at": item.observed_at.isoformat()} for (metric_key, _), items in latest_metric_values.items() if metric_key == key for item in items[:1]] for key in ("email_delivery_rate", "email_open_rate", "email_click_rate", "email_unsubscribe_rate")}
    campaign_performance = []
    for (metric_key, campaign_name), items in latest_metric_values.items():
        if campaign_name:
            observation = items[0]
            campaign_performance.append({"campaign": campaign_name, "metric": metric_key, "value": float(observation.metric_value), "source": observation.source, "provider": observation.provider, "observed_at": observation.observed_at.isoformat()})
    performance_alert_candidates = []
    unsubscribe_alert_candidates = []
    for (key, campaign), observations in latest_metric_values.items():
        if key == "email_unsubscribe_rate" and float(observations[0].metric_value) >= settings.MARKETING_UNSUBSCRIBE_ALERT_RATE:
            unsubscribe_alert_candidates.append({"campaign": campaign, "rate": float(observations[0].metric_value), "threshold": settings.MARKETING_UNSUBSCRIBE_ALERT_RATE, "source": observations[0].source, "observed_at": observations[0].observed_at.isoformat()})
        if key in {"email_delivery_rate", "email_open_rate", "email_click_rate", "social_reach", "social_engagement", "website_sessions", "content_assisted_conversions", "ghl_pipeline_value"} and len(observations) >= 2 and observations[1].metric_value > 0:
            previous = float(observations[1].metric_value)
            latest = float(observations[0].metric_value)
            drop_pct = (previous - latest) / previous * 100
            if drop_pct >= settings.MARKETING_LOW_PERFORMANCE_DROP_PCT:
                performance_alert_candidates.append({"metric": key, "campaign": campaign, "previous": previous, "latest": latest, "drop_pct": round(drop_pct, 2), "source": observations[0].source, "observed_at": observations[0].observed_at.isoformat()})

    delivery_failures = db.query(MarketingDelivery).filter(MarketingDelivery.status == "failed", MarketingDelivery.updated_at >= week_start).count()
    open_alerts = db.query(OperationalAlert).filter(OperationalAlert.team == "marketing", OperationalAlert.status == "open").all()
    return {
        "period_start": week_start.isoformat(),
        "period_end": now.isoformat(),
        "content_produced": created_count,
        "approval_turnaround_hours": round(sum(approval_durations) / len(approval_durations), 2) if approval_durations else None,
        "approval_turnaround_samples": len(approval_durations),
        "scheduled_publications": len(scheduled_content),
        "published_content": len(published_content),
        "publication_completion_rate": round(len(published_content & scheduled_content) / len(scheduled_content) * 100, 2) if scheduled_content else None,
        "content_revision_rate": round(revised_count / created_count * 100, 2) if created_count else None,
        "pending_approvals": len(pending),
        "overdue_approvals": [{"id": str(item.id), "title": item.title, "created_at": item.created_at.isoformat()} for item in overdue],
        "seo_movement": seo_movement,
        "social_engagement": [{"campaign": item.campaign_name, "value": float(item.metric_value), "source": item.source, "observed_at": item.observed_at.isoformat()} for item in engagement],
        "email_performance": email_performance,
        "campaign_performance": campaign_performance,
        "failed_integrations": [{"type": alert.alert_type, "source": alert.source, "message": alert.message, "severity": alert.severity, "created_at": alert.created_at.isoformat() if alert.created_at else None} for alert in open_alerts if any(token in alert.alert_type for token in ("failure", "outage", "provider", "stale"))],
        "open_alerts": [{"type": alert.alert_type, "source": alert.source, "message": alert.message, "severity": alert.severity, "created_at": alert.created_at.isoformat() if alert.created_at else None} for alert in open_alerts],
        "performance_alert_candidates": performance_alert_candidates,
        "unsubscribe_alert_candidates": unsubscribe_alert_candidates,
        "delivery_failures": delivery_failures,
        "sop_adherence": {"status": "measured" if brand_checks else "not_configured", "reviews": len(brand_checks), "passed": sum(1 for review in brand_checks if review.get("status") == "passed")},
        "brand_consistency": {"status": "measured" if brand_checks else "not_configured", "reviews": len(brand_checks), "consistent": sum(1 for review in brand_checks if review.get("brand_consistent") is True)},
        "source_metric_observations": len(metrics),
    }


@router.get("/intelligence/status", dependencies=[Depends(require_permission("marketing:research"))])
async def get_marketing_intelligence_status():
    return {"seo": _source_status("seo"), "social": _source_status("social")}


@router.get("/seo/overview", dependencies=[Depends(require_permission("marketing:seo"))])
async def get_seo_overview(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    observations = db.query(MarketingSeoObservation).order_by(MarketingSeoObservation.observed_at.desc()).limit(500).all()
    latest_by_type: dict[str, dict[str, Any]] = {}
    for observation in observations:
        latest_by_type.setdefault(observation.observation_type, {
            "value": observation.value,
            "keyword": observation.keyword,
            "url": observation.url,
            "source": observation.source,
            "observed_at": observation.observed_at.isoformat(),
        })
    return {
        "source_status": _source_status("seo"),
        "counts": {"observations": len(observations), "keywords": len({item.keyword for item in observations if item.keyword})},
        "latest_by_type": latest_by_type,
        "observations": [{"id": str(item.id), "observation_type": item.observation_type, "keyword": item.keyword, "url": item.url, "value": item.value, "source": item.source, "observed_at": item.observed_at.isoformat()} for item in observations[:100]],
    }


@router.post("/seo/observations", dependencies=[Depends(require_permission("marketing:seo"))])
async def create_seo_observation(request: SeoObservationRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    observation = MarketingSeoObservation(**request.model_dump(), created_by=current_user.id)
    db.add(observation)
    db.flush()
    db.add(MarketingIntelligenceEvent(entity_type="seo_observation", entity_id=observation.id, actor_id=current_user.id, event_type="created", details={"source": request.source, "observed_at": request.observed_at.isoformat()}))
    db.commit()
    return {"id": str(observation.id), "status": "recorded", "source": observation.source, "observed_at": observation.observed_at.isoformat()}


@router.post("/seo/recommendations", dependencies=[Depends(require_permission("marketing:research"))])
async def generate_seo_recommendations(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    observations = db.query(MarketingSeoObservation).order_by(MarketingSeoObservation.observed_at.desc()).limit(100).all()
    if not observations:
        return {"status": "not_configured", "message": "No source-backed SEO observations are available yet.", "recommendations": []}
    evidence = [{"type": item.observation_type, "keyword": item.keyword, "url": item.url, "value": item.value, "source": item.source, "observed_at": item.observed_at.isoformat()} for item in observations]
    prompt = f"""Create a concise weekly SEO recommendation list for ENY Marketing using only the evidence below.
Do not invent rankings, traffic, dates, competitors, or performance claims. Every recommendation must cite one or more exact source and observed_at pairs from the evidence. Identify missing data explicitly.
Evidence:
{json.dumps(evidence, default=str)}"""
    response = await ClaudeService().invoke(prompt=prompt, role_context="marketing", max_tokens=1800, temperature=0.2)
    return {"status": "generated", "source_count": len(evidence), "recommendations": response, "evidence": evidence}


@router.get("/social/overview", dependencies=[Depends(require_permission("marketing:social"))])
async def get_social_overview(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    mentions = db.query(MarketingSocialMention).order_by(MarketingSocialMention.observed_at.desc()).limit(500).all()
    counts = {classification: sum(1 for item in mentions if item.classification == classification) for classification in sorted(SOCIAL_CLASSIFICATIONS)}
    risk_counts = {risk: sum(1 for item in mentions if item.risk_level == risk) for risk in sorted(SOCIAL_RISK_LEVELS)}
    return {
        "source_status": _source_status("social"),
        "counts": {"mentions": len(mentions), "classifications": counts, "risk": risk_counts, "open_high_risk": sum(1 for item in mentions if item.status == "open" and item.risk_level in {"high", "critical"})},
        "mentions": [{"id": str(item.id), "platform": item.platform, "author": item.author, "text": item.text, "url": item.url, "matched_term": item.matched_term, "classification": item.classification, "sentiment": item.sentiment, "risk_level": item.risk_level, "status": item.status, "source": item.source, "observed_at": item.observed_at.isoformat()} for item in mentions[:100]],
    }


@router.post("/social/mentions", dependencies=[Depends(require_permission("marketing:social"))])
async def create_social_mention(request: SocialMentionRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    mention = MarketingSocialMention(**request.model_dump(exclude={"metadata"}), metadata_json=request.metadata, created_by=current_user.id)
    db.add(mention)
    db.flush()
    db.add(MarketingIntelligenceEvent(entity_type="social_mention", entity_id=mention.id, actor_id=current_user.id, event_type="created", details={"platform": request.platform, "risk_level": request.risk_level, "source": request.platform}))
    if mention.risk_level in {"high", "critical"}:
        db.add(OperationalAlert(team="marketing", alert_type="marketing_social_risk", severity="critical", source=mention.platform, message="High-risk social mention requires human review.", details={"mention_id": str(mention.id), "matched_term": mention.matched_term}))
    db.commit()
    return {"id": str(mention.id), "status": "routed_for_review" if mention.risk_level in {"high", "critical"} else "recorded", "risk_level": mention.risk_level}


def _video_asset_payload(asset: MarketingVideoAsset) -> dict[str, Any]:
    return {
        "id": str(asset.id), "title": asset.title, "original_filename": asset.original_filename,
        "mime_type": asset.mime_type, "size_bytes": asset.size_bytes, "status": asset.status,
        "transcript": asset.transcript, "duration_seconds": asset.duration_seconds, "transcript_segments": asset.transcript_segments,
        "transcript_provider": asset.transcript_provider, "generated_outputs": asset.generated_outputs,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


@router.get("/video/assets", dependencies=[Depends(require_any_permission("marketing:read", "video:read"))])
async def list_marketing_video_assets(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    assets = db.query(MarketingVideoAsset).order_by(MarketingVideoAsset.created_at.desc()).limit(100).all()
    return {"assets": [_video_asset_payload(asset) for asset in assets], "providers": _source_status("video")["providers"]}


@router.post("/video/assets", dependencies=[Depends(require_any_permission("marketing:write", "video:upload"))])
async def upload_marketing_video(
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
        title=title.strip(), original_filename=file.filename or "marketing-media",
        mime_type=file.content_type or "application/octet-stream", size_bytes=size_bytes,
        storage_path=storage_path, created_by=current_user.id,
    )
    db.add(asset)
    db.flush()
    db.add(MarketingIntelligenceEvent(entity_type="video_asset", entity_id=asset.id, actor_id=current_user.id, event_type="uploaded", details={"filename": asset.original_filename, "size_bytes": size_bytes, "storage": "private_supabase_storage"}))
    db.commit()
    return _video_asset_payload(asset)


@router.post("/video/assets/{asset_id}/transcribe", dependencies=[Depends(require_any_permission("marketing:write", "video:edit"))])
async def transcribe_marketing_video(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Marketing video asset not found")
    if asset.transcript:
        return _video_asset_payload(asset)
    result = await marketing_video_service.transcribe(asset.storage_path, asset.original_filename, asset.mime_type, asset.size_bytes)
    if result["status"] != "transcribed":
        asset.status = "transcription_required"
        db.add(MarketingIntelligenceEvent(entity_type="video_asset", entity_id=asset.id, actor_id=current_user.id, event_type="transcription_unavailable", details={"status": result["status"], "message": result["message"]}))
        db.commit()
        return {**_video_asset_payload(asset), "transcription": result}
    asset.transcript = result["text"]
    asset.duration_seconds = int(result["duration"]) if result.get("duration") is not None else None
    asset.transcript_segments = result["segments"]
    asset.transcript_provider = result["provider"]
    asset.status = "transcribed"
    db.add(MarketingIntelligenceEvent(entity_type="video_asset", entity_id=asset.id, actor_id=current_user.id, event_type="transcribed", details={"provider": result["provider"], "duration_seconds": result.get("duration"), "segment_count": len(result["segments"])}))
    db.commit()
    return _video_asset_payload(asset)


@router.post("/video/assets/{asset_id}/generate-pack", dependencies=[Depends(require_any_permission("marketing:write", "video:edit"))])
async def generate_marketing_video_pack(asset_id: UUID, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    asset = db.query(MarketingVideoAsset).filter(MarketingVideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Marketing video asset not found")
    if not asset.transcript:
        raise HTTPException(status_code=409, detail="Transcribe the source video before generating its content pack")
    knowledge = await retrieve_knowledge(db, ["marketing"], f"video repurposing brand voice social content {asset.title}", limit=8)
    prompt = f"""Repurpose this ENY Consulting recording into a reviewable content pack.
Use only the source transcript and approved Marketing knowledge for factual claims. Do not invent statistics, offers, or claims. Clip start/end values must refer to the supplied transcript segment timestamps. Return valid JSON only, in this shape:
{{"clips":[{{"title":"", "start_seconds":0, "end_seconds":30, "rationale":"", "caption":"", "description":"", "quote_card":"", "social_posts":[{{"platform":"linkedin", "copy":""}}]}}], "blog_excerpts":[{{"title":"", "excerpt":""}}]}}
Create up to 5 distinct clip recommendations and 3 blog excerpts. Include captions, titles, descriptions, quote cards, and platform-specific social copy where supported by the transcript.
Approved Marketing knowledge: {json.dumps(knowledge, default=str)}
Transcript segments: {json.dumps(asset.transcript_segments[:500], default=str)}
Transcript: {asset.transcript[:60000]}"""
    response = await ClaudeService().invoke(prompt=prompt, role_context="marketing", max_tokens=5000, temperature=0.3)
    try:
        generated = json.loads(response)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Content generation returned an invalid pack; retry after reviewing the transcript") from exc
    clips = generated.get("clips", []) if isinstance(generated, dict) else []
    excerpts = generated.get("blog_excerpts", []) if isinstance(generated, dict) else []
    if not isinstance(clips, list) or not isinstance(excerpts, list):
        raise HTTPException(status_code=502, detail="Content generation returned an invalid pack structure")

    outputs: list[dict[str, Any]] = []
    drafts: list[MarketingContentItem] = []
    source_documents = [{"title": asset.title, "source": asset.original_filename, "provider": asset.transcript_provider}]
    for clip in clips[:5]:
        if not isinstance(clip, dict):
            continue
        try:
            start_seconds = max(0, float(clip.get("start_seconds", 0)))
            end_seconds = float(clip.get("end_seconds", 0))
        except (TypeError, ValueError):
            continue
        if asset.duration_seconds is not None:
            end_seconds = min(end_seconds, float(asset.duration_seconds))
        if end_seconds <= start_seconds:
            continue
        output = {"kind": "clip", "title": str(clip.get("title") or "Video clip recommendation")[:240], "start_seconds": start_seconds, "end_seconds": end_seconds, "rationale": str(clip.get("rationale") or "")[:3000], "caption": str(clip.get("caption") or "")[:5000], "description": str(clip.get("description") or "")[:5000], "quote_card": str(clip.get("quote_card") or "")[:2000], "social_posts": clip.get("social_posts") if isinstance(clip.get("social_posts"), list) else []}
        outputs.append(output)
        content = json.dumps(output, ensure_ascii=True)
        drafts.append(MarketingContentItem(title=output["title"], content_type="repurposed_content", channel="linkedin", content=content, prompt=prompt, source_documents=source_documents, confidence="requires_review", created_by=current_user.id, campaign_owner_id=current_user.id))
        for post in output["social_posts"][:5]:
            if not isinstance(post, dict) or not str(post.get("copy") or "").strip():
                continue
            platform = str(post.get("platform") or "linkedin").lower()
            if platform not in CHANNELS or platform in {"email", "blog"}:
                continue
            drafts.append(MarketingContentItem(title=f"{output['title']} ({platform})", content_type="social_post", channel=platform, content=str(post.get("copy") or "")[:10000], prompt=prompt, source_documents=source_documents, confidence="requires_review", created_by=current_user.id, campaign_owner_id=current_user.id))
    for excerpt in excerpts[:3]:
        if not isinstance(excerpt, dict) or not excerpt.get("excerpt"):
            continue
        output = {"kind": "blog_excerpt", "title": str(excerpt.get("title") or f"{asset.title} excerpt")[:240], "excerpt": str(excerpt["excerpt"])[:50000]}
        outputs.append(output)
        drafts.append(MarketingContentItem(title=output["title"], content_type="blog_article", channel="blog", content=output["excerpt"], prompt=prompt, source_documents=source_documents, confidence="requires_review", created_by=current_user.id, campaign_owner_id=current_user.id))
    if not drafts:
        raise HTTPException(status_code=502, detail="Content generation produced no reviewable drafts")
    asset.generated_outputs = outputs
    asset.status = "pack_generated"
    db.add(asset)
    for draft in drafts:
        _apply_sensitive_claim_policy(draft)
        db.add(draft)
        db.flush()
        db.add(MarketingContentEvent(content_id=draft.id, actor_id=current_user.id, event_type="generated_from_video", details={"video_asset_id": str(asset.id), "status": "draft"}))
    db.add(MarketingIntelligenceEvent(entity_type="video_asset", entity_id=asset.id, actor_id=current_user.id, event_type="content_pack_generated", details={"outputs": len(outputs), "drafts": len(drafts), "approval_required": True}))
    db.commit()
    return {"asset": _video_asset_payload(asset), "draft_count": len(drafts), "drafts": [_serialize_content(draft) for draft in drafts]}


@router.post("/analytics/observations", dependencies=[Depends(require_permission("marketing:analytics"))])
async def create_campaign_metric_observation(request: CampaignMetricRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    observation = MarketingMetricObservation(
        metric_key=request.metric_key, metric_value=request.metric_value, campaign_name=request.campaign_name,
        channel=request.channel, provider=request.provider, source=request.source, observed_at=request.observed_at,
        metadata_json=request.metadata, created_by=current_user.id,
    )
    db.add(observation)
    db.flush()
    db.add(MarketingIntelligenceEvent(entity_type="campaign_metric", entity_id=observation.id, actor_id=current_user.id, event_type="recorded", details={"metric_key": request.metric_key, "provider": request.provider, "source": request.source, "observed_at": request.observed_at.isoformat()}))
    db.commit()
    return {"id": str(observation.id), "status": "recorded", "provider": observation.provider, "source": observation.source, "observed_at": observation.observed_at.isoformat()}

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
        contacts, inventory = await ghl_service.get_all_contacts()
        pipeline = await ghl_service.get_pipeline_data()
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        connected = inventory.get("status") == "connected"
        metrics = {
            "status": inventory.get("status", "not_configured"),
            "source": "GoHighLevel",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "totalLeads": len(contacts) if connected else None,
            "leadsThisMonth": sum(1 for contact in contacts if str(contact.get("dateAdded", "")).startswith(current_month)) if connected else None,
            "conversionRate": round(float(pipeline.get("conversion_rate", 0)) * 100, 2) if pipeline.get("status") == "connected" else None,
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
    """Return source-attributed observations and live GHL attribution, never sample metrics."""
    observed_at = datetime.now(timezone.utc).isoformat()
    observations = db.query(MarketingMetricObservation).order_by(MarketingMetricObservation.observed_at.desc()).limit(2000).all()
    expected_metrics = sorted(CAMPAIGN_METRICS)
    latest_metrics: dict[str, dict[str, Any]] = {}
    grouped_campaigns: dict[str, dict[str, Any]] = {}
    for observation in observations:
        metric_payload = {
            "value": float(observation.metric_value), "provider": observation.provider,
            "source": observation.source, "observed_at": observation.observed_at.isoformat(),
        }
        if observation.metric_key not in latest_metrics:
            latest_metrics[observation.metric_key] = metric_payload
        campaign_key = observation.campaign_name or observation.provider
        campaign = grouped_campaigns.setdefault(campaign_key, {"name": campaign_key, "metrics": {}, "sources": set(), "observed_at": observation.observed_at.isoformat()})
        campaign["metrics"].setdefault(observation.metric_key, metric_payload["value"])
        campaign["sources"].add(observation.source)
        campaign.setdefault("metric_sources", {}).setdefault(observation.metric_key, metric_payload)

    for campaign in grouped_campaigns.values():
        spend = campaign["metrics"].get("spend")
        revenue = campaign["metrics"].get("attributed_revenue")
        if spend is not None and spend > 0 and revenue is not None:
            spend_source = campaign["metric_sources"]["spend"]
            revenue_source = campaign["metric_sources"]["attributed_revenue"]
            campaign["metrics"]["roi"] = round((revenue - spend) / spend * 100, 2)
            campaign["metric_sources"]["roi"] = {
                "source": f"Calculated from {revenue_source['source']} and {spend_source['source']}",
                "observed_at": max(revenue_source["observed_at"], spend_source["observed_at"]),
            }

    metrics = {
        key: {"status": "configured", **latest_metrics[key]} if key in latest_metrics else {"status": "not_configured", "value": None, "provider": None, "source": None, "observed_at": None}
        for key in expected_metrics
    }
    campaigns = [{**campaign, "sources": sorted(campaign["sources"])} for campaign in grouped_campaigns.values()]

    ghl_configured = bool(settings.GHL_PRIVATE_TOKEN and settings.GHL_LOCATION_ID)
    lead_sources: dict[str, int] = {}
    leads_by_campaign: dict[str, int] = {}
    contacts_status = "not_configured"
    pipeline_status = "not_configured"
    pipeline_by_campaign: dict[str, dict[str, Any]] = {}
    if ghl_configured:
        try:
            contacts, inventory = await ghl_service.get_all_contacts()
            contacts_status = inventory.get("status", "error")
            for contact in contacts:
                source = str(contact.get("source") or "unknown")
                lead_sources[source] = lead_sources.get(source, 0) + 1
                campaign = contact.get("campaignName") or contact.get("campaign") or contact.get("utmCampaign")
                if campaign:
                    campaign_name = str(campaign)
                    leads_by_campaign[campaign_name] = leads_by_campaign.get(campaign_name, 0) + 1
            pipeline = await ghl_service.get_pipeline_data()
            pipeline_status = pipeline.get("status", "error")
            for opportunity in pipeline.get("opportunities", []):
                campaign = opportunity.get("campaignName") or opportunity.get("campaign") or opportunity.get("utmCampaign")
                if not campaign:
                    continue
                name = str(campaign)
                contribution = pipeline_by_campaign.setdefault(name, {"opportunities": 0, "value": 0.0})
                contribution["opportunities"] += 1
                contribution["value"] += float(opportunity.get("expectedValue") or opportunity.get("monetaryValue") or 0)
        except Exception:
            logger.exception("Unable to load live GHL Marketing attribution")
            contacts_status = "error"
            pipeline_status = "error"

    deliveries = db.query(MarketingDelivery).order_by(MarketingDelivery.created_at.desc()).limit(1000).all()
    email_deliveries = [delivery for delivery in deliveries if delivery.channel == "email"]
    sent_count = sum(int((delivery.metrics or {}).get("sent", 0) or 0) for delivery in email_deliveries if delivery.status == "sent")
    recipient_count = sum(delivery.recipient_count for delivery in email_deliveries)
    return {
        "observed_at": observed_at,
        "status": "configured" if observations or contacts_status == "connected" or email_deliveries else "not_configured",
        "metrics": metrics,
        "campaigns": campaigns,
        "attribution": {
            "leads_by_campaign": {"status": "configured" if leads_by_campaign else "not_configured", "source": "GoHighLevel", "observed_at": observed_at if contacts_status == "connected" else None, "items": [{"campaign": name, "leads": count} for name, count in sorted(leads_by_campaign.items())]},
            "lead_sources": {"status": contacts_status, "source": "GoHighLevel", "observed_at": observed_at if contacts_status == "connected" else None, "items": [{"source": name, "leads": count} for name, count in sorted(lead_sources.items())]},
            "pipeline_contribution": {"status": "configured" if pipeline_by_campaign else "not_configured" if pipeline_status == "connected" else pipeline_status, "source": "GoHighLevel", "observed_at": observed_at if pipeline_status == "connected" else None, "items": [{"campaign": name, **value} for name, value in sorted(pipeline_by_campaign.items())]},
        },
        "email_sends": {"status": "configured" if email_deliveries else "not_configured", "provider": "GHL", "records": len(email_deliveries), "recipients": recipient_count, "sent": sent_count, "send_completion_rate": round(sent_count / recipient_count * 100, 2) if recipient_count else None, "observed_at": observed_at if email_deliveries else None},
        "sources": {"ghl_contacts": contacts_status, "ghl_pipeline": pipeline_status, "metric_observations": len(observations), "delivery_records": len(deliveries)},
    }


@router.get("/operations/report", dependencies=[Depends(require_permission("marketing:analytics"))])
async def get_marketing_operations_report(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    report = _build_marketing_weekly_report(db, datetime.now(timezone.utc))
    report.pop("performance_alert_candidates", None)
    report.pop("unsubscribe_alert_candidates", None)
    return report


@router.post("/operations/weekly-review", dependencies=[Depends(require_permission("marketing:configure"))])
async def complete_marketing_weekly_review(request: WeeklyReviewRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    report = _build_marketing_weekly_report(db, now)
    for overdue in report["overdue_approvals"]:
        _raise_marketing_alert(db, "marketing_missing_approval", overdue["id"], "Marketing content exceeded the approval turnaround SLA.", overdue, "warning")
    for candidate in report["performance_alert_candidates"]:
        _raise_marketing_alert(db, "marketing_low_campaign_performance", candidate.get("campaign") or candidate["metric"], f"{candidate['metric'].replace('_', ' ')} dropped by {candidate['drop_pct']:.1f}% compared with the previous observation.", candidate, "warning")
    for candidate in report["unsubscribe_alert_candidates"]:
        _raise_marketing_alert(db, "marketing_unsubscribe_compliance", candidate.get("campaign") or "GHL", "Email unsubscribe rate exceeded the configured review threshold.", candidate, "critical")

    seo_sources = marketing_intelligence_service.configured_sources("seo")
    recent_seo = db.query(MarketingSeoObservation).filter(MarketingSeoObservation.observed_at >= now - timedelta(days=14)).count()
    if seo_sources and not recent_seo:
        for source in seo_sources:
            _raise_marketing_alert(db, "marketing_seo_provider_stale", source, "Configured SEO provider has no observations in the last 14 days; verify the connector or refresh job.", {"provider": source, "checked_at": now.isoformat()}, "warning")

    review = db.query(MarketingWeeklyReview).filter(MarketingWeeklyReview.week_start == request.week_start).first()
    if review:
        raise HTTPException(status_code=409, detail="A weekly Marketing review is already recorded for this week")
    review = MarketingWeeklyReview(week_start=request.week_start, summary=request.summary, decisions=request.decisions, metrics_snapshot={key: value for key, value in report.items() if key not in {"performance_alert_candidates", "unsubscribe_alert_candidates"}}, attendees=request.attendees, completed_by=current_user.id)
    db.add(review)
    db.flush()
    db.add(MarketingIntelligenceEvent(entity_type="weekly_review", entity_id=review.id, actor_id=current_user.id, event_type="completed", details={"week_start": request.week_start.isoformat(), "decision_count": len(request.decisions)}))
    db.commit()
    current_alerts = db.query(OperationalAlert).filter(OperationalAlert.team == "marketing", OperationalAlert.status == "open").all()
    report["open_alerts"] = [{"type": alert.alert_type, "source": alert.source, "message": alert.message, "severity": alert.severity, "created_at": alert.created_at.isoformat() if alert.created_at else None} for alert in current_alerts]
    report["failed_integrations"] = [alert for alert in report["open_alerts"] if any(token in alert["type"] for token in ("failure", "outage", "provider", "stale"))]
    report.pop("performance_alert_candidates", None)
    report.pop("unsubscribe_alert_candidates", None)
    return {"id": str(review.id), "week_start": request.week_start.isoformat(), "completed_at": review.created_at.isoformat() if review.created_at else now.isoformat(), "report": report}


@router.get("/operations/weekly-reviews", dependencies=[Depends(require_permission("marketing:read"))])
async def list_marketing_weekly_reviews(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    reviews = db.query(MarketingWeeklyReview).order_by(MarketingWeeklyReview.week_start.desc()).limit(52).all()
    return {"reviews": [{"id": str(item.id), "week_start": item.week_start.isoformat(), "summary": item.summary, "decisions": item.decisions, "metrics_snapshot": item.metrics_snapshot, "attendees": item.attendees, "completed_at": item.created_at.isoformat() if item.created_at else None} for item in reviews]}


@router.post("/operations/integration-health", dependencies=[Depends(require_permission("marketing:integrations"))])
async def record_marketing_integration_health(request: IntegrationHealthRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    seo_names = {"google_search_console", "ga4", "ahrefs", "semrush", "pagespeed", "dataforseo", "serpapi"}
    social_names = {"linkedin", "meta", "x", "youtube", "reddit", "slack", "buffer"}
    if request.provider not in seo_names | social_names | {"ghl", "whisper", "canva"}:
        raise HTTPException(status_code=422, detail="Unsupported Marketing integration provider")
    entity_id = uuid4()
    db.add(MarketingIntelligenceEvent(entity_type="provider_health", entity_id=entity_id, actor_id=current_user.id, event_type=request.status, details={"provider": request.provider, "observed_at": request.observed_at.isoformat(), "message": request.message}))
    alert_type = "marketing_seo_provider_outage" if request.provider in seo_names else "marketing_social_api_failure" if request.provider in social_names else "marketing_ghl_email_failure" if request.provider == "ghl" else "marketing_provider_failure"
    if request.status == "error":
        _raise_marketing_alert(db, alert_type, request.provider, request.message or f"{request.provider} reported an integration failure.", {"provider": request.provider, "observed_at": request.observed_at.isoformat()}, "critical")
    else:
        alert_types = [alert_type, "marketing_seo_provider_stale"] if request.provider in seo_names else [alert_type]
        open_alerts = db.query(OperationalAlert).filter(OperationalAlert.team == "marketing", OperationalAlert.alert_type.in_(alert_types), OperationalAlert.source == request.provider, OperationalAlert.status == "open").all()
        for alert in open_alerts:
            alert.status = "resolved"
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.acknowledged_by = current_user.id
    db.commit()
    return {"provider": request.provider, "status": request.status, "alert_type": alert_type if request.status == "error" else None}


@router.post("/content/{content_id}/brand-review", dependencies=[Depends(require_permission("marketing:research"))])
async def review_marketing_content_brand_alignment(content_id: UUID, request: BrandReviewRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    item = db.query(MarketingContentItem).filter(MarketingContentItem.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Marketing content not found")
    knowledge = await retrieve_knowledge(db, ["marketing"], f"brand voice visual identity claims social SEO compliance {item.title}", limit=8)
    prompt = f"""Evaluate this Marketing draft against only the approved ENY Marketing knowledge supplied. Do not invent policy. Return JSON with status (passed or needs_attention), brand_consistent (boolean), sop_adherent (boolean), issues (array), and evidence (array of source titles).
Draft title: {item.title}
Draft channel/type: {item.channel}/{item.content_type}
Draft content: {item.content}
Known sensitive claim categories: {json.dumps(item.compliance_flags or [])}
Approved Marketing knowledge: {json.dumps(knowledge, default=str)}"""
    answer = await ClaudeService().invoke(prompt=prompt, role_context="marketing", max_tokens=1200, temperature=0.1)
    try:
        result = json.loads(answer)
        if result.get("status") not in {"passed", "needs_attention"}:
            raise ValueError("Invalid review status")
    except (json.JSONDecodeError, AttributeError, ValueError):
        result = {"status": "manual_review", "brand_consistent": None, "sop_adherent": None, "issues": ["Automated review could not produce a verifiable structured result."], "evidence": []}
    result["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    result["reviewer_note"] = request.note
    result["knowledge_sources"] = [{"title": source.get("title"), "source": source.get("source")} for source in knowledge]
    db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="brand_compliance_review", details=result))
    db.commit()
    return result


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
        "requires_ceo_approval": item.requires_ceo_approval,
        "compliance_flags": item.compliance_flags or [],
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
    claim_flags = _sensitive_claim_flags(request.content)
    item = MarketingContentItem(
        title=request.title,
        content_type=request.content_type,
        channel=request.channel,
        content=request.content,
        due_at=request.due_at,
        prompt=request.prompt,
        source_documents=request.source_documents,
        confidence=request.confidence,
        requires_ceo_approval=bool(claim_flags),
        compliance_flags=claim_flags,
        created_by=current_user.id,
        campaign_owner_id=current_user.id,
    )
    db.add(item)
    db.flush()
    db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="created", details={"status": item.status}))
    db.commit()
    return _serialize_content(item)


@router.patch("/content/{content_id}", dependencies=[Depends(require_permission("marketing:write"))])
async def edit_marketing_content(
    content_id: UUID,
    request: ContentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    item = db.query(MarketingContentItem).filter(MarketingContentItem.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Marketing content not found")
    if item.status not in {"draft", "revision_required", "rejected"}:
        raise HTTPException(status_code=409, detail="Only draft, revision-required, or rejected content can be edited")
    values = request.model_dump(exclude_unset=True, exclude={"note"})
    next_type = values.get("content_type", item.content_type)
    next_channel = values.get("channel", item.channel)
    if next_type not in CONTENT_TYPES or next_channel not in CHANNELS:
        raise HTTPException(status_code=422, detail="Unsupported Marketing content type or channel")
    db.add(MarketingContentVersion(content_id=item.id, revision=item.revision, snapshot=_content_snapshot(item), change_note=request.note, changed_by=current_user.id))
    for key, value in values.items():
        setattr(item, key, value)
    item.revision += 1
    item.status = "draft"
    item.approved_by = None
    item.approved_at = None
    item.compliance_flags = _sensitive_claim_flags(item.content)
    item.requires_ceo_approval = bool(item.compliance_flags)
    db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="edited", details={"revision": item.revision, "note": request.note, "requires_ceo_approval": item.requires_ceo_approval}))
    db.commit()
    return _serialize_content(item)


@router.post("/content/{content_id}/submit", dependencies=[Depends(require_permission("marketing:write"))])
async def submit_marketing_content_for_review(content_id: UUID, note: str = Query(..., min_length=3, max_length=1000), db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    item = db.query(MarketingContentItem).filter(MarketingContentItem.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Marketing content not found")
    if item.status not in {"draft", "revision_required", "rejected"}:
        raise HTTPException(status_code=409, detail="Only draft or returned content can be submitted for review")
    previous_status = item.status
    item.status = "in_review"
    item.compliance_flags = _sensitive_claim_flags(item.content)
    item.requires_ceo_approval = bool(item.compliance_flags)
    db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="submitted_for_review", details={"from": previous_status, "to": item.status, "note": note, "requires_ceo_approval": item.requires_ceo_approval}))
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
    if item.status != "in_review" or request.status not in {"approved", "revision_required", "rejected"}:
        raise HTTPException(status_code=409, detail="Review decisions are only allowed for in-review content")
    if request.status == "approved" and item.requires_ceo_approval:
        raise HTTPException(status_code=409, detail="This content requires the dedicated CEO approval endpoint")
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


@router.post("/content/{content_id}/approve-sensitive", dependencies=[Depends(require_permission("marketing:approve")), Depends(require_permission("marketing:approve_sensitive"))])
async def approve_sensitive_marketing_content(content_id: UUID, request: SensitiveApprovalRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    item = db.query(MarketingContentItem).filter(MarketingContentItem.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Marketing content not found")
    if item.status != "in_review" or not item.requires_ceo_approval:
        raise HTTPException(status_code=409, detail="Only sensitive content in the review queue can receive CEO approval")
    sources = item.source_documents or []
    if not request.claims_verified or not any(isinstance(source, dict) and (source.get("source") or source.get("title")) for source in sources):
        raise HTTPException(status_code=422, detail="Attach at least one source and explicitly verify the sensitive claims before approval")
    item.status = "approved"
    item.approved_by = current_user.id
    item.approved_at = datetime.now(timezone.utc)
    db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="sensitive_approved", details={"approval_note": request.approval_note, "claims_verified": True, "compliance_flags": item.compliance_flags or []}))
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
    if item.status != "scheduled":
        raise HTTPException(status_code=409, detail="Content must be scheduled before it can be marked published")
    item.status = "published"
    db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="published", details={"note": request.note, "external_publish": False, "confirmation": "operator_recorded"}))
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


async def _create_marketing_delivery(
    request: DeliveryScheduleRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    allow_sensitive: bool = False,
):
    content = db.query(MarketingContentItem).filter(MarketingContentItem.id == request.content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Marketing content not found")
    if content.status != "approved":
        raise HTTPException(status_code=409, detail="Only approved content can be scheduled")
    if request.sensitive_broadcast and not allow_sensitive:
        raise HTTPException(status_code=409, detail="Use the CEO-only sensitive scheduling endpoint")
    if request.channel == "email":
        unsubscribe = urlsplit(request.unsubscribe_url or "")
        recipients_valid = bool(request.recipients) and all(item.get("contact_id") and item.get("email") and item.get("consent_confirmed") is True for item in request.recipients)
        if not request.consent_confirmed or not request.consent_evidence or not recipients_valid or not request.subject or unsubscribe.scheme != "https" or not unsubscribe.hostname:
            _raise_marketing_alert(db, "marketing_email_compliance", "GHL", "Email scheduling was blocked because consent or unsubscribe requirements were not met.", {"content_id": str(content.id), "recipient_count": len(request.recipients)}, "critical")
            db.commit()
            raise HTTPException(status_code=422, detail="Each email recipient needs a contact ID, address, and consent confirmation, plus consent evidence, subject, and an HTTPS unsubscribe URL")
        consent_results = []
        for recipient in request.recipients:
            consent_result = await ghl_service.validate_marketing_email_consent(str(recipient["contact_id"]), str(recipient["email"]))
            if not consent_result.get("eligible"):
                _raise_marketing_alert(db, "marketing_email_compliance", "GHL", "Email scheduling was blocked because a recipient did not pass CRM consent, identity, or suppression checks.", {"content_id": str(content.id), "contact_id": str(recipient["contact_id"]), "consent_status": consent_result.get("status")}, "critical")
                db.commit()
                if consent_result.get("status") == "not_configured":
                    raise HTTPException(status_code=503, detail="GHL_MARKETING_CONSENT_FIELD_ID must point to an explicit opt-in field before Marketing email can be scheduled")
                raise HTTPException(status_code=422, detail=f"Recipient {recipient['contact_id']} is not verified as eligible for Marketing email")
            consent_results.append({**recipient, "crm_consent_verified": True, "crm_consent_verified_at": datetime.now(timezone.utc).isoformat()})
        request.recipients = consent_results
    if request.sensitive_broadcast and not request.ceo_approval_note:
        raise HTTPException(status_code=422, detail="CEO approval note is required for a sensitive broadcast")
    provider = "ghl" if request.channel == "email" else "buffer"
    delivery = MarketingDelivery(
        content_id=content.id,
        channel=request.channel,
        provider=provider,
        status="scheduled",
        scheduled_at=request.scheduled_at,
        recipient_count=len(request.recipients),
        details={"recipients": request.recipients, "subject": request.subject, "unsubscribe_url": request.unsubscribe_url, "consent_confirmed": request.consent_confirmed, "consent_evidence": request.consent_evidence, "sensitive_broadcast": request.sensitive_broadcast, "ceo_approval_note": request.ceo_approval_note},
        created_by=current_user.id,
    )
    db.add(delivery)
    content.status = "scheduled"
    db.flush()
    db.add(MarketingContentEvent(content_id=content.id, actor_id=current_user.id, event_type="scheduled", details={"delivery_id": str(delivery.id), "provider": provider, "sensitive_broadcast": request.sensitive_broadcast}))
    db.add(MarketingDeliveryEvent(delivery_id=delivery.id, actor_id=current_user.id, event_type="scheduled", details={"provider": provider, "consent_confirmed": request.consent_confirmed, "sensitive_broadcast": request.sensitive_broadcast}))
    db.commit()
    return {"id": str(delivery.id), "status": delivery.status, "provider": provider}


@router.post("/deliveries/schedule", dependencies=[Depends(require_permission("marketing:send"))])
async def schedule_marketing_delivery(request: DeliveryScheduleRequest, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    return await _create_marketing_delivery(request, db, current_user)


@router.post("/deliveries/schedule-sensitive", dependencies=[Depends(require_permission("marketing:send")), Depends(require_permission("marketing:approve_sensitive"))])
async def schedule_sensitive_marketing_delivery(
    request: DeliveryScheduleRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    if not request.ceo_approval_note:
        raise HTTPException(status_code=422, detail="CEO approval note is required")
    request.sensitive_broadcast = True
    return await _create_marketing_delivery(request, db, current_user, allow_sensitive=True)


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
    if not content or content.status != "scheduled" or delivery.status != "scheduled":
        raise HTTPException(status_code=409, detail="Only approved and scheduled content can be executed")
    if delivery.scheduled_at > datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Delivery is not due yet")
    details = delivery.details or {}
    if delivery.provider == "ghl":
        unsubscribe = urlsplit(details.get("unsubscribe_url") or "")
        recipients = details.get("recipients") or []
        if not details.get("consent_confirmed") or not details.get("consent_evidence") or unsubscribe.scheme != "https" or not unsubscribe.hostname or not recipients:
            _raise_marketing_alert(db, "marketing_email_compliance", "GHL", "Email execution was blocked because stored consent or unsubscribe evidence is missing.", {"delivery_id": str(delivery.id)}, "critical")
            db.commit()
            raise HTTPException(status_code=409, detail="Stored consent and unsubscribe evidence are required before execution")
        for recipient in recipients:
            consent_result = await ghl_service.validate_marketing_email_consent(str(recipient.get("contact_id") or ""), str(recipient.get("email") or ""))
            if not consent_result.get("eligible"):
                _raise_marketing_alert(db, "marketing_email_compliance", "GHL", "Email execution was blocked because recipient consent or suppression status changed after scheduling.", {"delivery_id": str(delivery.id), "contact_id": recipient.get("contact_id"), "consent_status": consent_result.get("status")}, "critical")
                db.commit()
                raise HTTPException(status_code=409, detail=f"Recipient {recipient.get('contact_id')} is no longer eligible for Marketing email")
        result = await marketing_delivery_service.send_ghl_email(
            details.get("recipients", []),
            details.get("subject") or content.title,
            content.content,
            details["unsubscribe_url"],
        )
        success = result.get("status") == "sent"
    else:
        profile_ids = [value.strip() for value in settings.BUFFER_PROFILE_IDS.split(",") if value.strip()]
        result = await marketing_delivery_service.schedule_buffer(content.content, profile_ids, delivery.scheduled_at)
        success = result.get("status") == "scheduled"
    delivery.status = ("sent" if delivery.provider == "ghl" else "provider_scheduled") if success else "failed"
    delivery.sent_at = datetime.now(timezone.utc) if success and delivery.provider == "ghl" else None
    delivery.metrics = result
    delivery.error = None if success else "; ".join(result.get("errors", []))
    db.add(MarketingDeliveryEvent(delivery_id=delivery.id, actor_id=current_user.id, event_type=delivery.status if success else "failed", details=result))
    if success and delivery.provider == "ghl":
        content.status = "published"
        db.add(MarketingContentEvent(content_id=content.id, actor_id=current_user.id, event_type="published", details={"delivery_id": str(delivery.id), "provider": "ghl", "sent_at": datetime.now(timezone.utc).isoformat()}))
    if not success:
        alert_type = "marketing_ghl_email_failure" if delivery.provider == "ghl" else "marketing_social_publish_failure"
        _raise_marketing_alert(db, alert_type, delivery.provider, "Approved Marketing content delivery failed.", {"delivery_id": str(delivery.id), "result": result}, "critical")
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
    versions = db.query(MarketingContentVersion).filter(MarketingContentVersion.content_id == content_id).order_by(MarketingContentVersion.revision.desc()).all()
    return {
        "events": [{"id": str(event.id), "event_type": event.event_type, "details": event.details, "created_at": event.created_at.isoformat() if event.created_at else None} for event in events],
        "versions": [{"revision": version.revision, "snapshot": version.snapshot, "change_note": version.change_note, "changed_by": str(version.changed_by), "created_at": version.created_at.isoformat() if version.created_at else None} for version in versions],
    }


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
        _apply_sensitive_claim_policy(item)
        db.add(item)
        db.flush()
        db.add(MarketingContentEvent(content_id=item.id, actor_id=current_user.id, event_type="generated", details={"topic": topic, "source_count": len(source_documents)}))
        created.append(item)
    db.commit()
    return {"status": "generated", "count": len(created), "items": [_serialize_content(item) for item in created], "source_documents": source_documents}