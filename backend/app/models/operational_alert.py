# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/operational_alert.py

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class OperationalAlert(Base):
    __tablename__ = "operational_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team = Column(String, nullable=False, default="sales_enrollment", index=True)
    alert_type = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, default="critical")
    source = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    result_id = Column(UUID(as_uuid=True), ForeignKey("batch_execution_results.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String, nullable=False, default="open", index=True)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(UUID(as_uuid=True), nullable=True)
