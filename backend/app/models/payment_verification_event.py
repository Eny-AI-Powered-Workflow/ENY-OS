# C:\Users\Melody\Documents\ENY-OS\backend\app\models\payment_verification_event.py
import uuid

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class PaymentVerificationEvent(Base):
    __tablename__ = "payment_verification_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="payment_verification_events_idempotency_key_key"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    transaction_reference = Column(Text, nullable=False)
    verification_status = Column(String, nullable=False)
    provider_status = Column(String, nullable=False)
    reviewer_user_id = Column(UUID(as_uuid=True), nullable=False)
    idempotency_key = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))