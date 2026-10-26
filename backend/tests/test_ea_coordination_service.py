# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_ea_coordination_service.py
import os
import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.core.config import settings
from app.models.google_calendar import GoogleCalendarConnection, GoogleCalendarOAuthState
from app.services import ea_coordination_service as coordination_module
from app.services.ea_coordination_service import EACoordinationService


class FakeAsyncClient:
    calls = []
    calendar_status = 200
    post_payload = {"access_token": "test-access-token", "expires_in": 3600}

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
            json=self.post_payload,
            request=httpx.Request("POST", url),
        )

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        status = self.calendar_status if "calendar/v3" in url else 200
        if status >= 400:
            return httpx.Response(
                status,
                json={"error": {"code": status, "message": "Calendar access denied"}},
                request=httpx.Request("GET", url),
            )
        items = (
            [{"id": "event-1", "summary": "Planning", "start": {"dateTime": "2026-10-06T10:00:00Z"}}]
            if "calendar/v3" in url
            else [{"id": "task-1", "title": "Prepare agenda", "status": "needsAction"}]
        )
        return httpx.Response(200, json={"items": items}, request=httpx.Request("GET", url))


class FakeOAuthQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *_):
        return self

    def with_for_update(self):
        return self

    def first(self):
        if self.model is GoogleCalendarOAuthState:
            return self.db.state
        if self.model is GoogleCalendarConnection:
            return self.db.connection
        raise AssertionError(f"Unexpected query model: {self.model}")


class FakeOAuthDb:
    def __init__(self, state, connection=None):
        self.state = state
        self.connection = connection
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, model):
        return FakeOAuthQuery(self, model)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_shared_oauth_connection_reads_calendar_and_tasks(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.calendar_status = 200
    monkeypatch.setattr(coordination_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "EA_CALENDAR_BASE_URL", "https://www.googleapis.com/calendar/v3")
    monkeypatch.setattr(settings, "EA_CALENDAR_PATH", "calendars/primary/events")
    monkeypatch.setattr(settings, "EA_TASKS_BASE_URL", "https://tasks.googleapis.com/tasks/v1")
    monkeypatch.setattr(settings, "EA_TASKS_PATH", "lists/@default/tasks")

    service = EACoordinationService()
    monkeypatch.setattr(service, "_get_access_token", AsyncMock(return_value="test-access-token"))
    result = await service.get_coordination(MagicMock())

    assert result["calendar"]["status"] == "connected"
    assert result["calendar"]["items"][0]["id"] == "event-1"
    assert result["tasks"]["items"][0]["id"] == "task-1"
    assert result["source"] == "google_calendar_and_tasks"
    assert result["external_actions"] == "disabled"
    api_calls = [call for call in FakeAsyncClient.calls if call[0] == "GET"]
    assert len(api_calls) == 2
    assert all(call[2]["headers"]["Authorization"] == "Bearer test-access-token" for call in api_calls)
    calendar_params = next(call[2]["params"] for call in api_calls if "calendar/v3" in call[1])
    assert calendar_params["maxResults"] == "100"
    assert "attendees" not in calendar_params["fields"]


@pytest.mark.asyncio
async def test_service_reports_not_configured_without_shared_connection(monkeypatch):
    service = EACoordinationService()
    monkeypatch.setattr(service, "_get_access_token", AsyncMock(return_value=None))

    result = await service.get_coordination(MagicMock())

    assert result["calendar"] == {
        "status": "not_configured",
        "items": [],
        "confidence": "unavailable",
    }
    assert result["tasks"]["status"] == "not_configured"


@pytest.mark.asyncio
async def test_service_does_not_expose_google_oauth_configuration_values(monkeypatch):
    service = EACoordinationService()
    monkeypatch.setattr(
        service,
        "_get_access_token",
        AsyncMock(side_effect=ValueError("google_oauth_configuration_incomplete")),
    )

    result = await service.get_coordination(MagicMock())

    assert result["calendar"]["status"] == "error"
    assert result["calendar"]["error"] == "google_oauth_configuration_incomplete"
    assert "client-secret" not in repr(result)
    assert "refresh-token" not in repr(result)


@pytest.mark.asyncio
async def test_service_identifies_calendar_api_auth_failure_separately(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.calendar_status = 403
    monkeypatch.setattr(coordination_module.httpx, "AsyncClient", FakeAsyncClient)
    service = EACoordinationService()
    monkeypatch.setattr(service, "_get_access_token", AsyncMock(return_value="test-access-token"))

    result = await service.get_coordination(MagicMock())

    assert result["calendar"]["status"] == "error"
    assert result["calendar"]["error"] == "calendar_google_api_auth_failed"
    assert result["tasks"]["status"] == "connected"
    FakeAsyncClient.calendar_status = 200


def test_authorization_url_requests_read_only_calendar_and_tasks(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(
        settings,
        "GOOGLE_CALENDAR_REDIRECT_URI",
        "https://api.example.com/api/v1/calendar/oauth/callback",
    )
    monkeypatch.setattr(settings, "GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    db = MagicMock()

    authorization_url = EACoordinationService().authorization_url(
        db,
        "user-id",
        "https://app.example.com",
    )

    query = parse_qs(urlsplit(authorization_url).query)
    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["https://api.example.com/api/v1/calendar/oauth/callback"]
    assert set(query["scope"][0].split()) == set(EACoordinationService.REQUIRED_SCOPES)
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert len(query["state"][0]) >= 32
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_oauth_callback_encrypts_and_persists_shared_tokens(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.post_payload = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
        "scope": " ".join(EACoordinationService.REQUIRED_SCOPES),
    }
    monkeypatch.setattr(coordination_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(
        settings,
        "GOOGLE_CALENDAR_REDIRECT_URI",
        "https://api.example.com/api/v1/calendar/oauth/callback",
    )
    monkeypatch.setattr(settings, "GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    state = "single-use-oauth-state"
    state_row = SimpleNamespace(
        state_hash=hashlib.sha256(state.encode("utf-8")).hexdigest(),
        used_at=None,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        connected_by="ceo-user",
        redirect_origin="https://app.example.com",
    )
    db = FakeOAuthDb(state_row)
    service = EACoordinationService()

    redirect_origin = await service.complete_authorization(db, "authorization-code", state)

    connection = next(value for value in db.added if isinstance(value, GoogleCalendarConnection))
    assert redirect_origin == "https://app.example.com"
    assert state_row.used_at is not None
    assert connection.connected_by == "ceo-user"
    assert connection.status == "connected"
    assert service._decrypt(connection.access_token_encrypted) == "new-access-token"
    assert service._decrypt(connection.refresh_token_encrypted) == "new-refresh-token"
    assert set(connection.scopes) == set(EACoordinationService.REQUIRED_SCOPES)
    assert db.commits == 1


def test_redirect_uri_rejects_insecure_non_local_urls(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CALENDAR_REDIRECT_URI", "http://api.example.com/api/v1/calendar/oauth/callback")

    with pytest.raises(HTTPException) as exception:
        EACoordinationService()._redirect_uri()

    assert exception.value.status_code == 503


def test_google_refresh_tokens_are_encrypted(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(settings, "GOOGLE_TOKEN_ENCRYPTION_KEY", key)
    service = EACoordinationService()

    encrypted = service._encrypt("refresh-token")

    assert encrypted != "refresh-token"
    assert service._decrypt(encrypted) == "refresh-token"
