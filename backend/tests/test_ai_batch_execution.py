import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("CLAUDE_MODEL", "claude-3-opus-20240229")

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.ai import execute_approved_batch
from app.models.cohort_approval import CohortApproval


@pytest.mark.asyncio
async def test_execute_approved_batch_scores_only_approved_contacts(monkeypatch):
    approval = CohortApproval(
        id="01234567-89ab-cdef-0123-456789abcdef",
        user_id="12345678-89ab-cdef-0123-456789abcdef",
        cohort_name="Bootcamp waitlist Batch 1",
        source_filter="bootcamp",
        contact_ids=["contact-1", "contact-2"],
        batch_size=2,
        status="approved_for_scoring",
        decision="approved",
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = approval

    current_user = SimpleNamespace(id="12345678-89ab-cdef-0123-456789abcdef")

    async def fake_get_contacts_by_ids(contact_ids):
        assert contact_ids == ["contact-1", "contact-2"]
        return {
            "contact-1": {"id": "contact-1", "name": "Alice", "source": "bootcamp", "customFields": []},
            "contact-2": {"id": "contact-2", "name": "Bob", "source": "bootcamp", "customFields": []},
        }

    monkeypatch.setattr("app.api.v1.endpoints.ai.ghl_service.get_contacts_by_ids", fake_get_contacts_by_ids)
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.ghl_service.sync_enrollment_outcome",
        AsyncMock(return_value={"success": True}),
    )

    class FakeClaudeService:
        async def score_lead(self, lead_data):
            return {
                "score": 90,
                "category": "hot",
                "score_origin": "claude",
                "score_factors": {
                    "intent_score": 98,
                    "fit_score": 80,
                    "engagement_score": 90,
                },
                "reasoning": "Explicit interest and recent engagement are present.",
                "evidence": ["Requested a consultation", "Attended a webinar"],
                "unknowns": ["Budget"],
                "next_best_action": "Confirm program fit.",
            }

    monkeypatch.setattr("app.api.v1.endpoints.ai.ClaudeService", FakeClaudeService)

    result = await execute_approved_batch(
        approval_id="01234567-89ab-cdef-0123-456789abcdef",
        current_user=current_user,
        db=db,
    )

    assert result["status"] == "completed"
    assert result["processed_count"] == 2
    assert result["failed_count"] == 0
    assert len(result["results"]) == 2
    assert result["results"][0]["contact_id"] == "contact-1"
    assert result["results"][0]["score"] == 90
    assert result["results"][0]["category"] == "hot"

    from app.models.operational_alert import OperationalAlert
    alerts = [call.args[0] for call in db.add.call_args_list if call.args]
    assert any(
        isinstance(alert, OperationalAlert) and alert.alert_type == "hot_lead_ready"
        for alert in alerts
    )


@pytest.mark.asyncio
async def test_execute_approved_batch_does_not_score_when_ghl_lookup_fails(monkeypatch):
    approval = CohortApproval(
        id="01234567-89ab-cdef-0123-456789abcdef",
        user_id="12345678-89ab-cdef-0123-456789abcdef",
        cohort_name="Bootcamp waitlist Batch 1",
        source_filter="bootcamp",
        contact_ids=["contact-1"],
        batch_size=1,
        status="approved_for_scoring",
        decision="approved",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = approval

    async def fail_get_contacts(contact_ids):
        raise RuntimeError("GHL is temporarily unavailable")

    class UnexpectedClaudeService:
        def __init__(self):
            raise AssertionError("Scoring must not start when GHL lookup fails")

    monkeypatch.setattr("app.api.v1.endpoints.ai.ghl_service.get_contacts_by_ids", fail_get_contacts)
    monkeypatch.setattr("app.api.v1.endpoints.ai.ClaudeService", UnexpectedClaudeService)

    with pytest.raises(HTTPException) as error:
        await execute_approved_batch(
            approval_id=str(approval.id),
            current_user=SimpleNamespace(id=approval.user_id),
            db=db,
        )

    assert error.value.status_code == 502
    assert db.commit.call_count == 0


@pytest.mark.asyncio
async def test_execute_approved_batch_persists_claude_failure_detail_for_operator(monkeypatch):
    approval = CohortApproval(
        id="01234567-89ab-cdef-0123-456789abcdef",
        user_id="12345678-89ab-cdef-0123-456789abcdef",
        cohort_name="Bootcamp waitlist Batch 1",
        source_filter="bootcamp",
        contact_ids=["contact-1"],
        batch_size=1,
        status="approved_for_scoring",
        decision="approved",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = approval
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.ghl_service.get_contacts_by_ids",
        AsyncMock(return_value={
            "contact-1": {"id": "contact-1", "name": "Alice", "source": "bootcamp", "customFields": []},
        }),
    )

    class FailingClaudeService:
        async def score_lead(self, lead_data):
            raise RuntimeError("provider temporarily unavailable")

    monkeypatch.setattr("app.api.v1.endpoints.ai.ClaudeService", FailingClaudeService)

    result = await execute_approved_batch(
        approval_id=str(approval.id),
        current_user=SimpleNamespace(id=approval.user_id),
        db=db,
    )

    from app.models.operational_alert import OperationalAlert

    alerts = [call.args[0] for call in db.add.call_args_list if call.args]
    failure_alert = next(alert for alert in alerts if isinstance(alert, OperationalAlert))
    assert result["failed_count"] == 1
    assert failure_alert.details["error"] == "provider temporarily unavailable"
