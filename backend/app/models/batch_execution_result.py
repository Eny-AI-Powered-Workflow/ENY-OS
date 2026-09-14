# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/batch_execution_result.py
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class BatchExecutionResult(Base):
    __tablename__ = "batch_execution_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id = Column(UUID(as_uuid=True), ForeignKey("cohort_approvals.id", ondelete="CASCADE"), nullable=False)
    cohort_name = Column(String, nullable=False)
    contact_id = Column(String, nullable=False, index=True)
    contact_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    source = Column(String, nullable=True)
    score = Column(Integer, nullable=True)
    category = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    tags = Column(JSONB, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
