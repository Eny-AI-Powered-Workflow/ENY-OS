from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.batch_execution_service import retry_batch_result


class FakeQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *args, **kwargs):
        return self

    def with_for_update(self):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.row


class FakeDb:
    def __init__(self, pending):
        self.pending = pending
        self.added = []

    def query(self, model):
        return FakeQuery(self.pending if model.__name__ == "BatchRetry" else None)

    def add(self, item):
        self.added.append(item)

    def commit(self):
        return None


@pytest.mark.asyncio
async def test_retry_batch_result_retries_approved_contact(monkeypatch):
    result = SimpleNamespace(
        id="result-1",
        contact_id="contact-1",
        retry_count=1,
        status="failed",
        error="GHL update failed",
        score=None,
        category=None,
        queue_status="assigned",
        email=None,
        phone=None,
        source=None,
        tags=[],
    )
    approval = SimpleNamespace(id="approval-1")
    pending = SimpleNamespace(status="retry_pending")
    db = FakeDb(pending)

    monkeypatch.setattr(
        "app.services.batch_execution_service.ghl_service.get_contact",
        AsyncMock(return_value={
            "id": "contact-1",
            "name": "Alice Example",
            "email": "alice@example.com",
            "source": "bootcamp",
            "tags": ["bootcamp"],
            "customFields": [],
        }),
    )
    monkeypatch.setattr(
        "app.services.batch_execution_service.ghl_service.sync_enrollment_outcome",
        AsyncMock(return_value={"success": True}),
    )

    class FakeClaudeService:
        async def score_lead(self, lead_data):
            return {
                "score": 92,
                "category": "hot",
                "reasoning": "Explicit interest and fit evidence.",
                "score_factors": {
                    "intent_score": 100,
                    "fit_score": 80,
                    "engagement_score": 90,
                },
                "evidence": ["Requested a consultation"],
                "unknowns": ["Budget"],
                "next_best_action": "Book a consultation.",
            }

    monkeypatch.setattr("app.services.batch_execution_service.ClaudeService", FakeClaudeService)

    response = await retry_batch_result(result, approval, db)

    assert response["status"] == "scored"
    assert response["score"] == 92
    assert result.status == "scored"
    assert result.error is None
    assert pending.status == "attempted"
    assert any(getattr(item, "status", None) == "succeeded" for item in db.added)
