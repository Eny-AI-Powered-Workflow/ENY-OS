# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/ea_action.py

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class EAActionItem(Base):
    __tablename__ = "ea_action_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    action_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="open", index=True)
    priority = Column(String, nullable=False, default="normal")
    due_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    owner_id = Column(UUID(as_uuid=True), nullable=True)
    source = Column(String, nullable=False, default="ea_workspace")
    details = Column(JSONB, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EAActionEvent(Base):
    __tablename__ = "ea_action_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id = Column(UUID(as_uuid=True), ForeignKey("ea_action_items.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
