# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/ea_research_brief.py

import uuid

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class EAResearchBrief(Base):
    __tablename__ = "ea_research_briefs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    source_url = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    confidence = Column(String, nullable=False, default="unverified")
    status = Column(String, nullable=False, default="draft", index=True)
    requires_approval = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)
    review_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
