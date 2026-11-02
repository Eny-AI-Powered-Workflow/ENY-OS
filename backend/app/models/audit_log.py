# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/audit_log.py
from sqlalchemy import Column, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.sql import func
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # References auth.users.id
    permission_scope = Column(Text, nullable=False)
    granted = Column(Boolean, nullable=False)
    path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())