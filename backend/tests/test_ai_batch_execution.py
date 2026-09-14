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
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = approval

    current_user = SimpleNamespace(id="12345678-89ab-cdef-0123-456789abcdef")

    async def fake_get_all_contacts():
        return [
            {"id": "contact-1", "name": "Alice", "source": "bootcamp", "customFields": []},
            {"id": "contact-2", "name": "Bob", "source": "bootcamp", "customFields": []},
            {"id": "contact-9", "name": "Ignored", "source": "other", "customFields": []},
        ], ({"status": "connected"})

    monkeypatch.setattr("app.api.v1.endpoints.ai.ghl_service.get_all_contacts", fake_get_all_contacts)
    monkeypatch.setattr("app.api.v1.endpoints.ai.ghl_service.update_contact", AsyncMock(return_value=True))

    async def fake_score_lead(self, lead_data):
        return {"score": 84, "reasoning": "Strong fit", "recommended_tags": ["bootcamp"], "next_best_action": "Follow up"}

    monkeypatch.setattr("app.api.v1.endpoints.ai.ClaudeService.score_lead", fake_score_lead)

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
    assert result["results"][0]["score"] == 84
