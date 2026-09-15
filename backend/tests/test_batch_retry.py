from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.batch_execution_service import retry_batch_result


class FakeQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *args, **kwargs):
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
        return FakeQuery(self.pending)

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
        "app.services.batch_execution_service.ghl_service.update_contact",
        AsyncMock(return_value=True),
    )

    async def fake_trigger(self, workflow_name, data):
        return {"status": "success", "score": 92, "tags": ["hot"]}

    monkeypatch.setattr("app.services.batch_execution_service.N8NService.trigger_workflow", fake_trigger)

    response = await retry_batch_result(result, approval, db)

    assert response["status"] == "scored"
    assert response["score"] == 92
    assert result.status == "scored"
    assert result.error is None
    assert pending.status == "attempted"
    assert any(getattr(item, "status", None) == "succeeded" for item in db.added)
