# C:\Users\Melody\Documents\ENY-OS\backend\app\models\lead_assignment.py
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class LeadAssignment(Base):
    __tablename__ = "lead_assignments"

    contact_id = Column(String, primary_key=True)
    assigned_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    assigned_department = Column(String, nullable=False, index=True)
    assigned_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
