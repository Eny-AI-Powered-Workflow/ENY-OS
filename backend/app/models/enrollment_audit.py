# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/enrollment_audit.py
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


class EnrollmentAudit(Base):
    __tablename__ = "enrollment_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="RESTRICT"), nullable=False)
    result_id = Column(UUID(as_uuid=True), ForeignKey("batch_execution_results.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String, nullable=False, index=True)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
