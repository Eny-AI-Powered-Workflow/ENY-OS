# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/marketing_intelligence.py

import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class MarketingSeoObservation(Base):
    __tablename__ = "marketing_seo_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_type = Column(String, nullable=False, index=True)
    keyword = Column(String, nullable=True, index=True)
    url = Column(Text, nullable=True)
    value = Column(JSONB, nullable=False, default=dict)
    source = Column(String, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MarketingSocialMention(Base):
    __tablename__ = "marketing_social_mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String, nullable=False, index=True)
    external_id = Column(String, nullable=True)
    author = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    matched_term = Column(String, nullable=False, index=True)
    classification = Column(String, nullable=False, default="unclassified", index=True)
    sentiment = Column(String, nullable=False, default="unclassified")
    risk_level = Column(String, nullable=False, default="low", index=True)
    status = Column(String, nullable=False, default="open", index=True)
    source = Column(String, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MarketingIntelligenceEvent(Base):
    __tablename__ = "marketing_intelligence_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MarketingVideoAsset(Base):
    __tablename__ = "marketing_video_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(Text, nullable=False, unique=True)
    status = Column(String, nullable=False, default="uploaded", index=True)
    team = Column(String, nullable=False, default="marketing", index=True)
    audience = Column(String, nullable=False, default="marketing", index=True)
    transcript = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    transcript_segments = Column(JSONB, nullable=False, default=list)
    transcript_provider = Column(String, nullable=True)
    generated_outputs = Column(JSONB, nullable=False, default=list)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MarketingMetricObservation(Base):
    __tablename__ = "marketing_metric_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_key = Column(String, nullable=False, index=True)
    metric_value = Column(Numeric, nullable=False)
    campaign_name = Column(String, nullable=True, index=True)
    channel = Column(String, nullable=True)
    provider = Column(String, nullable=False)
    source = Column(String, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SocialPost(Base):
    __tablename__ = "social_posts"
    __table_args__ = (UniqueConstraint("platform", "account_id", "external_post_id", name="social_posts_external_identity_key"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=False)
    external_post_id = Column(String, nullable=False)
    content_id = Column(UUID(as_uuid=True), ForeignKey("marketing_content_items.id", ondelete="set null"), nullable=True)
    delivery_id = Column(UUID(as_uuid=True), ForeignKey("marketing_deliveries.id", ondelete="set null"), nullable=True)
    text = Column(Text, nullable=True)
    permalink = Column(Text, nullable=True)
    media_type = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint(
            "ghl_location_id",
            "platform",
            "external_account_id",
            name="social_accounts_external_identity_key",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ghl_location_id = Column(String, nullable=False)
    platform = Column(String, nullable=False, index=True)
    external_account_id = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    account_type = Column(String, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    is_expired = Column(Boolean, nullable=False, default=False)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    synced_at = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SocialAnalyticsSyncState(Base):
    __tablename__ = "social_analytics_sync_state"

    ghl_location_id = Column(String, primary_key=True)
    last_attempted_at = Column(DateTime(timezone=True), nullable=False)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    last_period_days = Column(Integer, nullable=True)
    accounts_synced = Column(Integer, nullable=False, default=0)
    posts_processed = Column(Integer, nullable=False, default=0)
    metrics_recorded = Column(Integer, nullable=False, default=0)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SocialMetricObservation(Base):
    __tablename__ = "social_metric_observations"
    __table_args__ = (
        UniqueConstraint("post_id", "metric_key", "observed_at", name="social_metric_observations_snapshot_key"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("social_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_key = Column(String, nullable=False, index=True)
    metric_value = Column(Numeric, nullable=False)
    unit = Column(String, nullable=False, default="count")
    provider = Column(String, nullable=False)
    source = Column(String, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
