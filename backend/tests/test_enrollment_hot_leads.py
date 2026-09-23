from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.api.v1.endpoints.enrollment import (
    BatchDecisionRequest,
    decide_batch_result,
    get_enrollment_hot_leads,
    get_batch_execution_results,
    get_enrollment_operations,
)
from app.models.batch_execution_result import BatchExecutionResult
from app.models.batch_retry import BatchRetry
from app.models.cohort_approval import CohortApproval
from app.models.enrollment_audit import EnrollmentAudit


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
            queue_status="new",
            assigned_user_id=None,
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
            queue_status="new",
            assigned_user_id=None,
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


@pytest.mark.asyncio
async def test_get_enrollment_operations_reports_live_operational_health():
    stale_time = datetime.now(timezone.utc) - timedelta(days=3)
    rows = [
        SimpleNamespace(
            id="row-1",
            contact_id="contact-1",
            contact_name="Alice Example",
            email=None,
            phone=None,
            source="bootcamp",
            score=92,
            category="hot",
            approval_id="approval-1",
            status="scored",
            queue_status="assigned",
            assigned_user_id=None,
            follow_up_status="not_started",
            error=None,
            retry_count=0,
            created_at=stale_time,
            updated_at=stale_time,
            follow_up_at=None,
        ),
        SimpleNamespace(
            id="row-2",
            contact_id="contact-2",
            contact_name="Bob Example",
            email="bob@example.com",
            phone="555-0002",
            source="free_training",
            score=84,
            category="hot",
            approval_id="approval-2",
            status="scored",
            queue_status="contacted",
            assigned_user_id="user-1",
            follow_up_status="tagged",
            error=None,
            retry_count=0,
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            updated_at=datetime.now(timezone.utc) - timedelta(hours=2),
            follow_up_at=datetime.now(timezone.utc) - timedelta(hours=3),
        ),
    ]

    def query(model):
        if model is BatchExecutionResult:
            return MagicMockQuery(rows)
        if model is EnrollmentAudit:
            return MagicMockQuery([])
        return MagicMockQuery([])

    db = SimpleNamespace(query=query)
    result = await get_enrollment_operations(limit=10, db=db, current_user=SimpleNamespace(id="user-1"))

    assert result["summary"]["ownerless_leads"] >= 1
    assert result["summary"]["stale_leads"] >= 1
    assert result["summary"]["data_quality_alerts"] >= 1
    assert result["health"]["queue_health"] in {"healthy", "warning", "degraded"}
    assert result["health"]["crm_status"] in {"connected", "not_configured", "degraded"}


@pytest.mark.asyncio
async def test_decide_batch_result_holds_failed_work_without_execution():
    result_row = SimpleNamespace(
        id="result-1",
        approval_id="approval-1",
        status="failed",
        failure_class=None,
        operating_decision="hold",
        recovery_owner_id=None,
        recovery_status="unassigned",
        last_action_at=None,
    )
    approval_row = SimpleNamespace(id="approval-1", user_id="user-1")
    retry_row = SimpleNamespace(
        status="retry_pending",
        operating_decision="hold",
        failure_class=None,
        recovery_owner_id=None,
    )

    class Query:
        def __init__(self, row):
            self.row = row

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self.row

    class Db:
        def __init__(self):
            self.added = []

        def query(self, model):
            return Query({
                BatchExecutionResult: result_row,
                CohortApproval: approval_row,
                BatchRetry: retry_row,
            }[model])

        def add(self, item):
            self.added.append(item)

        def commit(self):
            return None

    response = await decide_batch_result(
        result_id="result-1",
        request=BatchDecisionRequest(decision="hold", reason="Await CRM owner review", failure_class="crm_write"),
        db=Db(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response["status"] == "held"
    assert response["decision"] == "hold"
    assert result_row.failure_class == "crm_write"
    assert retry_row.status == "hold"
    assert result["sla"]["rules"]["assigned_contact_minutes"] == 60
    assert result["sla"]["alerts"][0]["code"] == "ownerless_hot_leads"
    assert result["reporting"]["response_compliance_percent"] == 0
    assert result["rollout"]["status"] == "needs_attention"


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
