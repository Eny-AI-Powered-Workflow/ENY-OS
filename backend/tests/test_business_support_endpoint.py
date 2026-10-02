import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

import asyncio
from datetime import datetime, timezone
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.deps import require_permission
from app.api.v1 import endpoints
from app.api.v1.endpoints.business_support import (
    PaystackPaymentVerificationCreate,
    PilotReviewCreate,
    create_pilot_review,
    get_pilot_reviews,
    require_business_support_enabled,
    router,
    verify_paystack_payment,
)
from app.api.v1.router import api_router
from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.business_support_pilot_review import BusinessSupportPilotReview
from app.models.payment_verification_event import PaymentVerificationEvent

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "0035_business_support_pilot_reviews.sql"
PAYMENT_MIGRATION_PATH = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "0036_business_support_payment_verifications.sql"


def _route_scope(route) -> set[str]:
    return {
        cell.cell_contents
        for dependency in route.dependant.dependencies
        for cell in (dependency.call.__closure__ or ())
        if isinstance(cell.cell_contents, str)
    }


def test_business_support_overview_is_registered_and_permission_gated():
    endpoint = next(route for route in router.routes if route.path == "/overview")
    registered_paths = {route.path for route in api_router.routes}

    assert "/business-support/overview" in registered_paths
    assert "business_support:dashboard:read" in _route_scope(endpoint)


def test_business_support_overview_returns_only_read_only_metadata():
    endpoint = next(route for route in router.routes if route.path == "/overview")
    result = asyncio.run(endpoint.endpoint())

    assert result["mode"] == "read_only"
    assert result["available_views"] == ["payment_records"]
    assert "students" not in result
    assert "records" not in result


def test_pilot_review_routes_use_separate_read_and_write_scopes():
    routes = {
        (route.path, method): route
        for route in router.routes if hasattr(route, "dependant")
        for method in route.methods
    }

    assert "business_support:pilot:read" in _route_scope(routes[("/pilot/reviews", "GET")])
    assert "business_support:pilot:write" in _route_scope(routes[("/pilot/reviews", "POST")])


def test_payment_verification_routes_require_the_audited_payment_scope():
    routes = {
        (route.path, method): route
        for route in router.routes if hasattr(route, "dependant")
        for method in route.methods
    }

    assert "payments:verify" in _route_scope(routes[("/payments/verification-status", "GET")])
    assert "payments:verify" in _route_scope(routes[("/payments/verify", "POST")])


def test_business_support_routes_are_default_off_and_audit_before_feature_gate(monkeypatch):
    monkeypatch.setattr(settings, "BUSINESS_SUPPORT_ENABLED", False)
    routes = [route for route in router.routes if hasattr(route, "dependant")]

    with pytest.raises(HTTPException) as error:
        require_business_support_enabled()
    assert error.value.status_code == 503
    assert error.value.detail["code"] == "feature_disabled"

    for route in routes:
        dependencies = route.dependant.dependencies
        assert dependencies[0].call.__name__ == "permission_checker"
        assert dependencies[1].call is require_business_support_enabled


def test_business_support_feature_gate_opens_only_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "BUSINESS_SUPPORT_ENABLED", True)
    assert require_business_support_enabled() is None


def test_denied_business_support_scope_is_forbidden_and_audited():
    query = Mock()
    query.join.return_value = query
    query.filter.return_value = query
    query.first.return_value = None
    database = Mock()
    database.query.return_value = query
    current_user = type("User", (), {"id": uuid4()})()
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/api/v1/business-support/overview",
        "headers": [],
        "query_string": b"",
    })

    with pytest.raises(HTTPException) as error:
        require_permission("business_support:dashboard:read")(current_user, database, request)

    assert error.value.status_code == 403
    audit = database.add.call_args.args[0]
    assert isinstance(audit, AuditLog)
    assert audit.permission_scope == "business_support:dashboard:read"
    assert audit.granted is False
    assert audit.path == "/api/v1/business-support/overview"
    database.commit.assert_called_once()


def test_denied_payment_verification_permission_is_audited():
    query = Mock()
    query.join.return_value = query
    query.filter.return_value = query
    query.first.return_value = None
    database = Mock()
    database.query.return_value = query
    current_user = SimpleNamespace(id=uuid4())
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/business-support/payments/verify",
        "headers": [],
        "query_string": b"",
    })

    with pytest.raises(HTTPException) as error:
        require_permission("payments:verify")(current_user, database, request)

    assert error.value.status_code == 403
    audit = database.add.call_args.args[0]
    assert isinstance(audit, AuditLog)
    assert audit.permission_scope == "payments:verify"
    assert audit.granted is False
    assert audit.path == "/api/v1/business-support/payments/verify"
    database.commit.assert_called_once()


def test_pilot_review_submission_is_idempotent_and_attributes_reviewer():
    submission_id = uuid4()
    reviewer_id = uuid4()
    payload = PilotReviewCreate(
        id=submission_id,
        scenario="shadow_output",
        workflow_name="eny-prog-onboard",
        result="expected",
        false_positive=False,
        missing_data=False,
        processing_seconds=45,
        escalation_quality=4,
    )
    query = Mock()
    query.filter.return_value = query
    query.first.side_effect = [None, None]
    database = Mock()
    database.query.return_value = query
    database.refresh.side_effect = lambda review: setattr(review, "created_at", datetime.now(timezone.utc))
    reviewer = SimpleNamespace(id=reviewer_id)

    first = create_pilot_review(payload, database, reviewer)
    stored_review = database.add.call_args.args[0]
    query.first.side_effect = None
    query.first.return_value = stored_review
    duplicate = create_pilot_review(payload, database, reviewer)

    assert first["duplicate"] is False
    assert duplicate["duplicate"] is True
    assert stored_review.reviewer_user_id == reviewer_id
    assert "student_name" not in first["review"]
    assert "customer_email" not in first["review"]
    database.add.assert_called_once()
    database.commit.assert_called_once()


def test_pilot_review_summary_reports_shadow_and_contingency_metrics():
    now = datetime.now(timezone.utc)
    reviews = [
        BusinessSupportPilotReview(
            id=uuid4(), scenario="shadow_output", workflow_name="eny-prog-onboard", result="expected",
            false_positive=False, missing_data=False, processing_seconds=40, escalation_quality=4, created_at=now,
        ),
        BusinessSupportPilotReview(
            id=uuid4(), scenario="provider_unavailable", workflow_name=None, result="unexpected",
            false_positive=True, missing_data=True, processing_seconds=60, escalation_quality=2, created_at=now,
        ),
        BusinessSupportPilotReview(
            id=uuid4(), scenario="missing_recording", workflow_name=None, result="not_run",
            false_positive=None, missing_data=None, processing_seconds=None, escalation_quality=None, created_at=now,
        ),
    ]
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = reviews
    database = Mock()
    database.query.return_value = query

    result = get_pilot_reviews(7, database)

    assert result["summary"] == {
        "total_reviews": 3,
        "expected": 1,
        "unexpected": 1,
        "not_run": 1,
        "false_positive_samples": 1,
        "missing_data_samples": 1,
        "average_processing_seconds": 50.0,
        "average_escalation_quality": 3.0,
    }


def test_pilot_review_storage_has_no_student_or_provider_identifier_fields():
    columns = set(BusinessSupportPilotReview.__table__.columns.keys())
    assert not columns.intersection({"student_id", "student_name", "customer_email", "provider_record_id"})


def test_programs_manager_receives_pilot_read_but_not_write_scope():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    manager_grant = re.search(
        r"where\s+r\.name\s*=\s*'programs_manager'\s+and\s+p\.scope\s+in\s*\(([^)]*)\)",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )

    assert manager_grant
    manager_scopes = set(re.findall(r"'([^']+)'", manager_grant.group(1)))
    assert "business_support:dashboard:read" in manager_scopes
    assert "business_support:pilot:read" in manager_scopes
    assert "business_support:pilot:write" not in manager_scopes


@pytest.mark.asyncio
async def test_payment_verification_is_provider_checked_and_idempotent(monkeypatch):
    idempotency_key = uuid4()
    reviewer_id = uuid4()
    payload = PaystackPaymentVerificationCreate(reference="paystack-ref-1", idempotency_key=idempotency_key)
    stored_events = {}
    query = Mock()
    query.filter.return_value = query
    query.first.side_effect = lambda: stored_events.get(idempotency_key)
    database = Mock()
    database.query.return_value = query
    database.add.side_effect = lambda event: stored_events.setdefault(idempotency_key, event)
    database.refresh.side_effect = lambda event: setattr(event, "created_at", datetime.now(timezone.utc))
    verify_provider = Mock(return_value=None)

    async def verify(reference):
        verify_provider(reference)
        return {
            "provider": "paystack",
            "reference": reference,
            "provider_status": "success",
            "currency": "NGN",
            "amount_minor": 500000,
            "transaction_date": "2026-10-01T10:00:00Z",
            "verification_status": "verified",
        }

    monkeypatch.setattr(endpoints.business_support.student_payments_service, "verify_paystack_transaction", verify)
    reviewer = SimpleNamespace(id=reviewer_id)

    first = await verify_paystack_payment(payload, database, reviewer)
    second = await verify_paystack_payment(payload, database, reviewer)

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert first["verification"]["verification_status"] == "verified"
    assert first["verification"]["reviewer_id"] == str(reviewer_id)
    assert isinstance(stored_events[idempotency_key], PaymentVerificationEvent)
    assert verify_provider.call_count == 1
    database.add.assert_called_once()
    database.commit.assert_called_once()


def test_payment_verification_migration_restricts_table_to_service_role():
    sql = PAYMENT_MIGRATION_PATH.read_text(encoding="utf-8").lower()

    assert "enable row level security" in sql
    assert "revoke all on payment_verification_events from anon, authenticated" in sql
    assert "grant select, insert on payment_verification_events to service_role" in sql
    assert "unique" in sql and "idempotency_key" in sql