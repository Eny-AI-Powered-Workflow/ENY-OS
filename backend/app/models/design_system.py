# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/design_system.py

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class DesignSystemDocument(Base):
    __tablename__ = "design_system_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    audience = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    source_status = Column(String, nullable=False, default="unverified")
    source_reference = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DesignSystemDocumentVersion(Base):
    __tablename__ = "design_system_document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("design_system_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False)
    change_note = Column(Text, nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignSystemDocumentEvent(Base):
    __tablename__ = "design_system_document_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("design_system_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
