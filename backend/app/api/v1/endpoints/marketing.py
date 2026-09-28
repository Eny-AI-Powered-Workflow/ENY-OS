# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/marketing.py
from datetime import datetime, timezone
import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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


@router.get("/video/assets", dependencies=[Depends(require_permission("marketing:read"))])
async def list_marketing_video_assets(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    assets = db.query(MarketingVideoAsset).order_by(MarketingVideoAsset.created_at.desc()).limit(100).all()
    return {"assets": [_video_asset_payload(asset) for asset in assets], "providers": _source_status("video")["providers"]}


@router.post("/video/assets", dependencies=[Depends(require_permission("marketing:write"))])
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


@router.post("/video/assets/{asset_id}/transcribe", dependencies=[Depends(require_permission("marketing:write"))])
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


@router.post("/video/assets/{asset_id}/generate-pack", dependencies=[Depends(require_permission("marketing:write"))])
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