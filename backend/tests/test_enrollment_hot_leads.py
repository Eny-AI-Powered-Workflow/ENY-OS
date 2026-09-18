from types import SimpleNamespace

import pytest

from app.api.v1.endpoints.enrollment import get_enrollment_hot_leads, get_batch_execution_results


@pytest.mark.asyncio
async def test_get_enrollment_hot_leads_uses_execution_results(monkeypatch):
    rows = [
        SimpleNamespace(
            id="row-1",
            contact_id="contact-1",
            contact_name="Alice Example",
            email="alice@example.com",
            phone="555-0001",
            source="bootcamp",
            score=92,
            category="hot",
            approval_id="approval-1",
            status="scored",
            tags=["hot", "approved-batch"],
            created_at="2025-01-01T00:00:00Z",
        ),
        SimpleNamespace(
            id="row-2",
            contact_id="contact-2",
            contact_name="Bob Example",
            email="bob@example.com",
            phone="555-0002",
            source="free_training",
            score=80,
            category="warm",
            approval_id="approval-1",
            status="scored",
            tags=["warm"],
            created_at="2025-01-01T00:00:00Z",
        ),
    ]

    query = MagicMockQuery(rows)
    db = SimpleNamespace(query=lambda model: query)

    result = await get_enrollment_hot_leads(limit=10, db=db, current_user=SimpleNamespace(id="user-1"))

    assert result["total"] == 1
    assert result["leads"][0]["contact_id"] == "contact-1"
    assert result["leads"][0]["score"] == 92


@pytest.mark.asyncio
async def test_hot_leads_marks_uuid_owner_as_current_user():
    rows = [
        SimpleNamespace(
            id="row-1",
            contact_id="contact-1",
            contact_name="Alice Example",
            email="alice@example.com",
            phone=None,
            source="bootcamp",
            score=92,
            category="hot",
            approval_id="approval-1",
            status="scored",
            queue_status="assigned",
            assigned_user_id="user-1",
            tags=["hot"],
            created_at="2025-01-01T00:00:00Z",
        ),
    ]

    query = MagicMockQuery(rows)
    db = SimpleNamespace(query=lambda model: query)

    result = await get_enrollment_hot_leads(limit=10, db=db, current_user=SimpleNamespace(id="user-1"))

    assert result["leads"][0]["assigned_to_current_user"] is True


@pytest.mark.asyncio
async def test_get_batch_execution_results_returns_recent_ledger():
    rows = [
        SimpleNamespace(
            id="result-1",
            approval_id="approval-1",
            cohort_name="Bootcamp waitlist",
            contact_id="contact-1",
            contact_name="Alice Example",
            source="bootcamp",
            status="scored",
            score=92,
            category="hot",
            error=None,
            retry_count=0,
            created_at="2025-01-01T00:00:00Z",
        )
    ]

    query = MagicMockQuery(rows)
    db = SimpleNamespace(query=lambda model: query)

    result = await get_batch_execution_results(limit=10, db=db, current_user=SimpleNamespace())

    assert result["total"] == 1
    assert result["results"][0]["contact_id"] == "contact-1"
    assert result["results"][0]["status"] == "scored"


class MagicMockQuery:
    def __init__(self, rows):
        self.rows = rows
        self._filtered_rows = rows

    def filter(self, *args, **kwargs):
        self._filtered_rows = list(self._filtered_rows)
        for arg in args:
            if hasattr(arg, "left") and hasattr(arg, "right"):
                field = getattr(arg.left, "key", None)
                value = arg.right
                if hasattr(value, "value"):
                    value = value.value

                if field == "status":
                    allowed = value if isinstance(value, (list, tuple, set)) else [value]
                    self._filtered_rows = [row for row in self._filtered_rows if getattr(row, "status", None) in allowed]
                elif field == "category":
                    self._filtered_rows = [row for row in self._filtered_rows if getattr(row, "category", None) == value]
                elif field == "score":
                    self._filtered_rows = [row for row in self._filtered_rows if getattr(row, "score", 0) >= value]
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self._filtered_rows
