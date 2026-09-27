# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/marketing_intelligence.py

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
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
