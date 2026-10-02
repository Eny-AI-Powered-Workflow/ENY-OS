# C:\Users\Melody\Documents\ENY-OS\backend\app\models\business_support_pilot_review.py
import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class BusinessSupportPilotReview(Base):
    __tablename__ = "business_support_pilot_reviews"
    __table_args__ = (
        CheckConstraint(
            "scenario in ('shadow_output', 'provider_unavailable', 'malformed_or_duplicate_webhook', "
            "'delayed_payment_evidence', 'missing_recording', 'rejected_action')",
            name="business_support_pilot_review_scenario_check",
        ),
        CheckConstraint(
            "workflow_name is null or workflow_name in ('eny-prog-onboard', 'eny-prog-monitor')",
            name="business_support_pilot_review_workflow_check",
        ),
        CheckConstraint(
            "result in ('expected', 'unexpected', 'not_run')",
            name="business_support_pilot_review_result_check",
        ),
        CheckConstraint(
            "scenario <> 'shadow_output' or workflow_name is not null",
            name="business_support_pilot_review_shadow_workflow_check",
        ),
        CheckConstraint(
            "processing_seconds is null or processing_seconds >= 0",
            name="business_support_pilot_review_duration_check",
        ),
        CheckConstraint(
            "escalation_quality is null or escalation_quality between 1 and 5",
            name="business_support_pilot_review_escalation_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario = Column(String, nullable=False)
    workflow_name = Column(String, nullable=True)
    result = Column(String, nullable=False)
    false_positive = Column(Boolean, nullable=True)
    missing_data = Column(Boolean, nullable=True)
    processing_seconds = Column(Integer, nullable=True)
    escalation_quality = Column(SmallInteger, nullable=True)
    reviewer_user_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))