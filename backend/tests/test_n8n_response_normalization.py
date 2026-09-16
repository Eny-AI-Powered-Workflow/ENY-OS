# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_n8n_response_normalization.py
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.n8n_service import N8NService


@pytest.mark.asyncio
async def test_n8n_one_item_array_response_is_normalized():
    response = httpx.Response(
        200,
        json=[{"status": "success", "action": "enrollment_follow_up"}],
        request=httpx.Request("POST", "http://n8n.test/webhook/eny-enrollment-follow-up"),
    )

    with patch("app.services.n8n_service.httpx.AsyncClient") as client_type:
        client = client_type.return_value.__aenter__.return_value
        client.post = AsyncMock(return_value=response)
        result = await N8NService().trigger_workflow(
            "eny-enrollment-follow-up",
            {"contact_id": "contact-1"},
        )

    assert result["status"] == "success"
    assert result["action"] == "enrollment_follow_up"
