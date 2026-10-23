# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/operational_alert_user_state.py
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class OperationalAlertUserState(Base):
    __tablename__ = "operational_alert_user_states"

    alert_id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
