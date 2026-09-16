# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/cohort_approval.py

import uuid

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class CohortApproval(Base):
    __tablename__ = "cohort_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Supabase owns auth.users outside this application's SQLAlchemy metadata.
    user_id = Column(UUID(as_uuid=True), nullable=False)
    cohort_name = Column(String, nullable=False)
    source_filter = Column(String, nullable=False)
    contact_ids = Column(JSONB, nullable=False)
    batch_size = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="approved_for_scoring")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)