# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_ceo_account_management.py
import os
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.ceo import (
    RoleAssignmentRequest,
    assign_account_roles,
    router,
)


def _required_scopes(route):
    return {
        cell.cell_contents
        for dependency in route.dependant.dependencies
        for cell in (dependency.call.__closure__ or ())
        if isinstance(cell.cell_contents, str)
    }


def test_account_management_routes_require_users_manage():
    routes = {
        route.path: route
        for route in router.routes
        if hasattr(route, "dependant")
    }

    assert "users:manage" in _required_scopes(routes["/accounts"])
    assert "users:manage" in _required_scopes(routes["/accounts/{user_id}/roles"])


@pytest.mark.asyncio
async def test_ceo_role_cannot_be_assigned_through_account_management():
    with pytest.raises(HTTPException) as error:
        await assign_account_roles(
            user_id=uuid4(),
            request=RoleAssignmentRequest(roles=["ceo"]),
            db=None,
        )

    assert error.value.status_code == 400
