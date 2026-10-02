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
from app.api.v1.endpoints.business_support import PilotReviewCreate, create_pilot_review, get_pilot_reviews, router
from app.api.v1.router import api_router
from app.models.audit_log import AuditLog
from app.models.business_support_pilot_review import BusinessSupportPilotReview

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "0035_business_support_pilot_reviews.sql"


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