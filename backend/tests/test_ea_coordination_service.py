# C:/Users/Melody/Documents/ENY-OS/backend/tests/test_ea_coordination_service.py
import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

import httpx
import pytest

from app.core.config import settings
from app.services import ea_coordination_service as coordination_module
from app.services.ea_coordination_service import EACoordinationService


class FakeAsyncClient:
    calls = []

    def __init__(self, *args, **kwargs):
        self.options = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return httpx.Response(
            200,
            json={"access_token": "test-access-token", "expires_in": 3600},
            request=httpx.Request("POST", url),
        )

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        items = (
            [{"id": "event-1", "summary": "Planning", "start": {"dateTime": "2026-10-06T10:00:00Z"}}]
            if "calendar/v3" in url
            else [{"id": "task-1", "title": "Prepare agenda", "status": "needsAction"}]
        )
        return httpx.Response(200, json={"items": items}, request=httpx.Request("GET", url))


@pytest.mark.asyncio
async def test_shared_oauth_token_reads_calendar_and_tasks(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr(coordination_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_REFRESH_TOKEN", "refresh-token")
    monkeypatch.setattr(settings, "EA_CALENDAR_BASE_URL", "https://www.googleapis.com/calendar/v3")
    monkeypatch.setattr(settings, "EA_CALENDAR_PATH", "calendars/primary/events")
    monkeypatch.setattr(settings, "EA_TASKS_BASE_URL", "https://tasks.googleapis.com/tasks/v1")
    monkeypatch.setattr(settings, "EA_TASKS_PATH", "lists/@default/tasks")

    service = EACoordinationService()
    result = await service.get_coordination()

    assert result["calendar"]["status"] == "connected"
    assert result["calendar"]["items"][0]["id"] == "event-1"
    assert result["tasks"]["items"][0]["id"] == "task-1"
    assert result["source"] == "google_calendar_and_tasks"
    assert result["external_actions"] == "disabled"
    token_calls = [call for call in FakeAsyncClient.calls if call[0] == "POST"]
    api_calls = [call for call in FakeAsyncClient.calls if call[0] == "GET"]
    assert len(token_calls) == 1
    assert len(api_calls) == 2
    assert all(call[2]["headers"]["Authorization"] == "Bearer test-access-token" for call in api_calls)
    calendar_params = next(call[2]["params"] for call in api_calls if "calendar/v3" in call[1])
    assert calendar_params["maxResults"] == "100"
    assert "attendees" not in calendar_params["fields"]


@pytest.mark.asyncio
async def test_service_reports_unconfigured_without_oauth_credentials(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_REFRESH_TOKEN", "")

    result = await EACoordinationService().get_calendar()

    assert result == {
        "status": "not_configured",
        "items": [],
        "confidence": "unavailable",
    }


@pytest.mark.asyncio
async def test_service_does_not_expose_google_oauth_configuration_values(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_REFRESH_TOKEN", "refresh-token")

    result = await EACoordinationService().get_calendar()

    assert result["status"] == "error"
    assert result["error"] == "google_oauth_configuration_incomplete"
    assert "client-id" not in repr(result)
    assert "refresh-token" not in repr(result)
