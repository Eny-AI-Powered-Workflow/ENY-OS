from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.v1.endpoints.enrollment import (
    BatchDecisionRequest,
    LeadAssignmentRequest,
    _transition_queue_state,
    assign_enrollment_crm_lead,
    assign_hot_lead,
    decide_batch_result,
    follow_up_hot_lead,
    get_enrollment_hot_leads,
    get_enrollment_leads,
    get_batch_execution_results,
    get_enrollment_operations,
    ingest_ghl_contact,
)
from app.models.batch_execution_result import BatchExecutionResult
from app.models.batch_retry import BatchRetry
from app.models.cohort_approval import CohortApproval
from app.models.enrollment_audit import EnrollmentAudit
from app.models.lead_assignment import LeadAssignment
from app.models.permission import Permission


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

    db = SimpleNamespace(query=query, add=lambda _: None, commit=lambda: None)
    result = await get_enrollment_operations(limit=10, db=db, current_user=SimpleNamespace(id="user-1"))

    assert result["summary"]["ownerless_leads"] >= 1
    assert result["summary"]["stale_leads"] >= 1
    assert result["summary"]["data_quality_alerts"] >= 1
    assert result["health"]["queue_health"] in {"healthy", "warning", "degraded"}
    assert result["health"]["crm_status"] in {"connected", "not_configured", "degraded"}
    assert result["monitoring"]["lead_intake"]["today"] == 1
    assert result["monitoring"]["no_contact_aging"]["over_24_hours"] == 1
    assert result["monitoring"]["conversion_by_source"]["free_training"]["closed"] == 0
    assert result["monitoring"]["owner_workload"][0]["owner_id"] in {"user-1", "unassigned"}
    assert result["sla"]["rules"]["assigned_contact_minutes"] == 60
    assert result["sla"]["alerts"][0]["code"] == "ownerless_hot_leads"
    assert result["reporting"]["response_compliance_percent"] == 0
    assert result["rollout"]["status"] == "needs_attention"


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

        def join(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return self.row

        def all(self):
            return self.row if isinstance(self.row, list) else [self.row]

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


def test_queue_transition_helper_rejects_skipped_states():
    result = SimpleNamespace(queue_status="assigned", last_action_at=None)

    with pytest.raises(Exception, match="Invalid queue transition"):
        _transition_queue_state(result, "closed", "user-1", "Skipped qualification")

    previous = _transition_queue_state(result, "contacted", "user-1", "Contact completed")
    assert previous == "assigned"
    assert result.queue_status == "contacted"


@pytest.mark.asyncio
async def test_assign_hot_lead_assigns_team_member_and_audits_writeback(monkeypatch):
    from uuid import UUID

    assigned_user_id = UUID("00000000-0000-0000-0000-000000000002")
    result = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        contact_id="contact-1",
        category="hot",
        queue_status="new",
        assigned_user_id=None,
        last_action_at=None,
    )

    class Query:
        def __init__(self, row):
            self.row = row

        def filter(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        def first(self):
            return self.row

        def all(self):
            return self.row if isinstance(self.row, list) else [self.row]

    class Db:
        def __init__(self):
            self.added = []
            self.committed = False

        def query(self, model):
            if model is BatchExecutionResult:
                return Query(result)
            if model is Permission:
                return Query(SimpleNamespace(scope="sales:leads:assign"))
            if model is LeadAssignment:
                return Query(None)
            return Query((assigned_user_id,))

        def add(self, item):
            self.added.append(item)

        def commit(self):
            self.committed = True

    db = Db()
    monkeypatch.setattr(
        "app.api.v1.endpoints.enrollment.ghl_service.sync_enrollment_outcome",
        AsyncMock(return_value={"success": False, "error": "Contact not found in GHL"}),
    )

    response = await assign_hot_lead(
        result_id=result.id,
        request=LeadAssignmentRequest(assigned_user_id=assigned_user_id, department="sales"),
        db=db,
        current_user=SimpleNamespace(id="operator-1"),
    )

    assert response["status"] == "assigned"
    assert "GHL synchronization failed" in response["warning"]
    assert result.assigned_user_id == assigned_user_id
    assert result.assigned_department == "sales"
    assert db.committed is True
    audit_events = [item for item in db.added if isinstance(item, EnrollmentAudit)]
    assert any(item.event_type == "ghl_writeback_failed" for item in audit_events)
    assert any(item.event_type == "hot_lead_assigned" for item in audit_events)


@pytest.mark.asyncio
async def test_sales_lead_cannot_assign_to_enrollment_department():
    from fastapi import HTTPException
    from uuid import UUID

    result = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        category="hot",
        queue_status="new",
    )

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        def first(self):
            return result

        def all(self):
            return [SimpleNamespace(scope="sales:leads:assign")]

    class Db:
        def query(self, model):
            return Query()

        def add(self, _):
            pass

        def commit(self):
            pass

    with pytest.raises(HTTPException) as error:
        await assign_hot_lead(
            result_id=result.id,
            request=LeadAssignmentRequest(
                assigned_user_id=UUID("00000000-0000-0000-0000-000000000002"),
                department="enrollment",
            ),
            db=Db(),
            current_user=SimpleNamespace(id="sales-lead"),
        )

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_get_enrollment_leads_returns_assignments_and_filters_my_leads(monkeypatch):
    assignment = SimpleNamespace(
        contact_id="contact-1",
        assigned_user_id="user-1",
        assigned_department="sales",
    )
    calls = []

    class Query:
        def __init__(self, rows):
            self.rows = rows

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self.rows

        def scalar(self):
            return 0

    class Db:
        def query(self, model):
            if getattr(model, "key", None) == "contact_id":
                return Query([("contact-1",)])
            if model is LeadAssignment:
                return Query([assignment])
            return Query([])

    async def fake_get_leads(**kwargs):
        calls.append(kwargs)
        return {
            "leads": [{"id": "contact-1", "name": "Alice"}],
            "next_cursor": None,
            "has_more": False,
            "pages_scanned": 1,
        }

    monkeypatch.setattr("app.api.v1.endpoints.enrollment.ghl_service.get_enrollment_lead_page", fake_get_leads)

    response = await get_enrollment_leads(
        limit=100,
        search="alice",
        mine=True,
        db=Db(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert calls[0]["contact_ids"] == {"contact-1"}
    assert response["leads"][0]["assigned_user_id"] == "user-1"
    assert response["leads"][0]["assigned_department"] == "sales"


@pytest.mark.asyncio
async def test_assign_enrollment_crm_lead_records_owner_and_audit(monkeypatch):
    from uuid import UUID

    assigned_user_id = UUID("00000000-0000-0000-0000-000000000002")
    batch_result = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000003"),
        contact_id="contact-1",
        category="hot",
        queue_status="new",
        last_action_at=None,
    )

    class Query:
        def __init__(self, row):
            self.row = row

        def filter(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        def first(self):
            return self.row

        def all(self):
            return self.row if isinstance(self.row, list) else [self.row]

    class Db:
        def __init__(self):
            self.added = []

        def query(self, model):
            if model is Permission:
                return Query(SimpleNamespace(scope="sales:leads:assign"))
            if model is LeadAssignment:
                return Query(None)
            if model is BatchExecutionResult:
                return Query([batch_result])
            return Query((assigned_user_id,))

        def add(self, item):
            self.added.append(item)

        def commit(self):
            pass

    monkeypatch.setattr(
        "app.api.v1.endpoints.enrollment.ghl_service.get_contact",
        AsyncMock(return_value={"contact": {"id": "contact-1"}}),
    )
    db = Db()
    response = await assign_enrollment_crm_lead(
        contact_id="contact-1",
        request=LeadAssignmentRequest(assigned_user_id=assigned_user_id, department="sales"),
        db=db,
        current_user=SimpleNamespace(id="sales-lead"),
    )

    assert response["assigned_user_id"] == str(assigned_user_id)
    assignment = next(item for item in db.added if isinstance(item, LeadAssignment))
    assert assignment.contact_id == "contact-1"
    assert assignment.assigned_department == "sales"
    assert batch_result.queue_status == "assigned"
    assert batch_result.assigned_user_id == assigned_user_id
    assert any(item.event_type == "lead_assignment_changed" for item in db.added if isinstance(item, EnrollmentAudit))


@pytest.mark.asyncio
async def test_sales_lead_cannot_take_a_lead_from_enrollment():
    from fastapi import HTTPException
    from uuid import UUID

    existing_assignment = SimpleNamespace(assigned_department="enrollment")

    class Query:
        def __init__(self, row):
            self.row = row

        def filter(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        def first(self):
            return self.row

        def all(self):
            return [self.row]

    class Db:
        def query(self, model):
            if model is Permission:
                return Query(SimpleNamespace(scope="sales:leads:assign"))
            if model is LeadAssignment:
                return Query(existing_assignment)
            return Query(None)

        def add(self, _):
            pass

        def commit(self):
            pass

    with pytest.raises(HTTPException) as error:
        await assign_enrollment_crm_lead(
            contact_id="contact-1",
            request=LeadAssignmentRequest(
                assigned_user_id=UUID("00000000-0000-0000-0000-000000000002"),
                department="sales",
            ),
            db=Db(),
            current_user=SimpleNamespace(id="sales-lead"),
        )

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_completed_follow_up_cannot_be_triggered_twice(monkeypatch):
    from uuid import UUID
    from fastapi import HTTPException

    result = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        contact_id="contact-1",
        approval_id=None,
        assigned_user_id="user-1",
        queue_status="assigned",
        follow_up_status="tagged",
    )

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def with_for_update(self):
            return self

        def first(self):
            return result

    db = SimpleNamespace(query=lambda model: Query())
    with pytest.raises(HTTPException, match="already been notified"):
        await follow_up_hot_lead(
            result_id=result.id,
            db=db,
            current_user=SimpleNamespace(id="user-1"),
        )


@pytest.mark.asyncio
async def test_notify_sales_action_creates_internal_alert_without_contact_email(monkeypatch):
    from uuid import UUID
    from app.models.operational_alert import OperationalAlert

    result = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        contact_id="contact-2",
        approval_id=None,
        assigned_user_id="user-1",
        queue_status="assigned",
        follow_up_status="not_started",
        score=91,
        source="webinar",
    )

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def with_for_update(self):
            return self

        def first(self):
            return result

    db = SimpleNamespace(
        query=lambda model: Query(),
        added=[],
        add=lambda value: db.added.append(value),
        commit=lambda: None,
    )
    tag_contact = AsyncMock(return_value=True)
    monkeypatch.setattr("app.api.v1.endpoints.enrollment.ghl_service.tag_contact", tag_contact)
    chat_message = AsyncMock(return_value={"status": "sent"})
    monkeypatch.setattr("app.api.v1.endpoints.enrollment.google_chat_service.send_message", chat_message)

    response = await follow_up_hot_lead(
        result_id=result.id,
        db=db,
        current_user=SimpleNamespace(id="user-1"),
    )

    tag_contact.assert_awaited_once_with("contact-2", ["eny-follow-up-queued"])
    assert response["status"] == "team_notified"
    assert response["lead_contacted"] is False
    assert response["google_chat"] == {"status": "sent"}
    assert response["warning"] is None
    chat_message.assert_awaited_once()
    assert "assigned hot lead" in chat_message.await_args.args[0]
    assert "No email or text" in response["message"]
    assert result.queue_status == "assigned"
    assert result.lifecycle_stage == "queued"
    assert any(
        isinstance(item, OperationalAlert) and item.alert_type == "sales_team_notification"
        for item in db.added
    )


@pytest.mark.asyncio
async def test_notify_sales_reports_google_chat_delivery_failure(monkeypatch):
    import httpx
    from uuid import UUID
    from app.models.operational_alert import OperationalAlert

    result = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000003"),
        contact_id="contact-3",
        approval_id=None,
        assigned_user_id="user-1",
        queue_status="assigned",
        follow_up_status="not_started",
        score=91,
        source="webinar",
    )

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def with_for_update(self):
            return self

        def first(self):
            return result

    db = SimpleNamespace(
        query=lambda model: Query(),
        added=[],
        add=lambda value: db.added.append(value),
        commit=lambda: None,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.enrollment.ghl_service.tag_contact",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.enrollment.google_chat_service.send_message",
        AsyncMock(side_effect=httpx.ConnectError("connection refused")),
    )

    response = await follow_up_hot_lead(
        result_id=result.id,
        db=db,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response["google_chat"]["status"] == "failed"
    assert "Google Chat delivery status is failed" in response["warning"]
    assert any(
        isinstance(item, OperationalAlert) and item.alert_type == "google_chat_delivery_failure"
        for item in db.added
    )


@pytest.mark.asyncio
async def test_ghl_intake_duplicate_is_reported_even_while_pending(monkeypatch):
    from unittest.mock import MagicMock
    from app.core.config import settings

    monkeypatch.setattr(settings, "GHL_INBOUND_WEBHOOK_TOKEN", "test-token")
    intake = SimpleNamespace(contact_id="contact-3", status="pending_review")
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.query.return_value.filter.return_value.first.return_value = intake

    response = await ingest_ghl_contact(
        {"contact": {"id": "contact-3", "source": "webinar"}},
        x_ghl_webhook_token="test-token",
        db=db,
    )

    assert response["duplicate"] is True
    assert response["status"] == "pending_review"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_ghl_intake_rejects_missing_webhook_token(monkeypatch):
    from fastapi import HTTPException
    from app.core.config import settings

    monkeypatch.setattr(settings, "GHL_INBOUND_WEBHOOK_TOKEN", "test-token")
    db = SimpleNamespace(execute=AsyncMock())

    with pytest.raises(HTTPException) as error:
        await ingest_ghl_contact({"contact": {"id": "contact-4"}}, None, db)

    assert error.value.status_code == 401


def test_ghl_reconciliation_uses_recent_creation_or_update_dates():
    from app.api.v1.endpoints.enrollment import _contact_is_recent

    cutoff = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert _contact_is_recent({"dateAdded": "2026-09-01T00:00:00Z", "dateUpdated": "2026-10-02T00:00:00Z"}, cutoff)
    assert not _contact_is_recent({"dateAdded": "not-a-date", "dateUpdated": "2026-09-30T00:00:00Z"}, cutoff)


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

    def join(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self._filtered_rows
