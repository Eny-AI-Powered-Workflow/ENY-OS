# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_n8n_response_normalization.py
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import BackgroundTasks, HTTPException
from unittest.mock import AsyncMock, Mock

from app.api.v1.endpoints import agents
from app.services.n8n_service import N8NService


@pytest.mark.asyncio
async def test_n8n_one_item_array_response_is_normalized():
    response = httpx.Response(
        200,
        json=[{"status": "success", "action": "enrollment_follow_up"}],
        request=httpx.Request("POST", "http://n8n.test/webhook/eny-prog-onboard"),
    )

    with patch("app.services.n8n_service.httpx.AsyncClient") as client_type:
        client = client_type.return_value.__aenter__.return_value
        client.post = AsyncMock(return_value=response)
        result = await N8NService().trigger_workflow(
            "eny-prog-onboard",
            {"contact_id": "contact-1"},
        )

    assert result["status"] == "success"
    assert result["action"] == "enrollment_follow_up"


@pytest.mark.asyncio
async def test_enrollment_followup_stays_blocked_until_side_effects_are_idempotent():
    result = await N8NService().trigger_workflow(
        "eny-enrollment-follow-up",
        {"approval_id": "approval-1"},
    )

    assert result["status"] == "error"
    assert "not registered" in result["error"].lower()


@pytest.mark.asyncio
async def test_agent_gateway_preserves_bad_gateway_for_n8n_failure(monkeypatch):
    monkeypatch.setattr(
        agents.n8n_service,
        "trigger_workflow",
        AsyncMock(return_value={"status": "error", "error": "provider unavailable"}),
    )
    db = Mock()

    with pytest.raises(HTTPException) as error:
        await agents.trigger_agent_workflow(
            "eny-customer-success-checkin",
            {},
            BackgroundTasks(),
            db,
            {"id": "test-user"},
        )

    assert error.value.status_code == 502
    db.commit.assert_called_once()
    db.rollback.assert_not_called()
