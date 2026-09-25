# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/marketing_content.py

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class MarketingContentItem(Base):
    __tablename__ = "marketing_content_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    content_type = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    content = Column(Text, nullable=False)
    campaign_owner_id = Column(UUID(as_uuid=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    prompt = Column(Text, nullable=True)
    source_documents = Column(JSONB, nullable=False, default=list)
    confidence = Column(String, nullable=False, default="unverified")
    revision = Column(Integer, nullable=False, default=1)
    approval_required = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MarketingContentEvent(Base):
    __tablename__ = "marketing_content_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("marketing_content_items.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
