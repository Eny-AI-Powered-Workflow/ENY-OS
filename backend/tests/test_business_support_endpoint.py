import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

import asyncio
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.deps import require_permission
from app.api.v1.endpoints.business_support import router
from app.api.v1.router import api_router
from app.models.audit_log import AuditLog


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