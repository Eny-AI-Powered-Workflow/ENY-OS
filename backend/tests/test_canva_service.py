# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_canva_service.py

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

from fastapi import HTTPException
import pytest
from cryptography.fernet import Fernet
from starlette.requests import Request

from app.api.v1.endpoints.canva import _oauth_completion_url, _post_connect_redirect
from app.core.config import settings
from app.db.base import Base
from app.models.design_system import CanvaOAuthState
from app.services import canva_service as canva_module
from app.services.canva_service import CanvaService


def test_oauth_user_foreign_key_resolves_to_supabase_auth_users():
    user_id = CanvaOAuthState.__table__.c.user_id
    foreign_key = next(iter(user_id.foreign_keys))

    assert foreign_key.column is Base.metadata.tables["auth.users"].c.id


def test_oauth_return_url_uses_allowed_frontend_origin(monkeypatch):
    monkeypatch.setattr(settings, "BACKEND_CORS_ORIGINS", "https://eny-os.vercel.app")
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/canva/connect",
        "headers": [(b"origin", b"https://eny-os.vercel.app")],
        "query_string": b"",
        "server": ("api.test", 443),
        "client": ("127.0.0.1", 12345),
        "scheme": "https",
    })

    assert _post_connect_redirect(request) == (
        "https://eny-os.vercel.app/canva/oauth-complete"
    )


def test_oauth_completion_redirect_normalizes_previously_saved_dashboard_path(monkeypatch):
    monkeypatch.setattr(settings, "BACKEND_CORS_ORIGINS", "https://eny-os.vercel.app")

    assert _oauth_completion_url(
        "https://eny-os.vercel.app/dashboard/videographer",
        "connected",
    ) == "https://eny-os.vercel.app/canva/oauth-complete?canva=connected"


def test_oauth_return_url_rejects_unapproved_origin(monkeypatch):
    monkeypatch.setattr(settings, "BACKEND_CORS_ORIGINS", "https://eny-os.vercel.app")
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/canva/connect",
        "headers": [(b"origin", b"https://attacker.example")],
        "query_string": b"",
        "server": ("api.test", 443),
        "client": ("127.0.0.1", 12345),
        "scheme": "https",
    })

    with pytest.raises(HTTPException) as error:
        _post_connect_redirect(request)

    assert error.value.status_code == 400


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeQuery:
    def __init__(self, connection):
        self.connection = connection
        self.locked = False
        self.refreshed = False

    def filter(self, *args, **kwargs):
        return self

    def with_for_update(self):
        self.locked = True
        return self

    def populate_existing(self):
        self.refreshed = True
        return self

    def first(self):
        return self.connection


class FakeDb:
    def __init__(self, connection):
        self.connection = connection
        self.queries = []
        self.commits = 0

    def query(self, model):
        query = FakeQuery(self.connection)
        self.queries.append(query)
        return query

    def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_expired_shared_token_refreshes_under_lock_and_rotates_both_tokens(monkeypatch):
    service = CanvaService()
    encryption_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(settings, "CANVA_TOKEN_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setattr(settings, "CANVA_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "CANVA_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(settings, "CANVA_REDIRECT_URI", "https://backend.test/api/v1/canva/oauth/callback")
    connection = SimpleNamespace(
        status="connected",
        token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        access_token_encrypted=service._encrypt("old-access"),
        refresh_token_encrypted=service._encrypt("old-refresh"),
        scopes=["design:content:write"],
        updated_at=None,
    )
    db = FakeDb(connection)
    received_refresh_token = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, auth, headers, data):
            assert auth == ("client-id", "client-secret")
            received_refresh_token.append(data["refresh_token"])
            return FakeResponse({
                "access_token": "new-access",
                "refresh_token": "rotated-refresh",
                "expires_in": 3600,
                "scope": "design:content:write design:meta:read",
            })

    monkeypatch.setattr(canva_module.httpx, "AsyncClient", FakeAsyncClient)

    result = await service.access_token(db, uuid4())

    assert result == "new-access"
    assert received_refresh_token == ["old-refresh"]
    assert db.queries[1].locked is True
    assert db.queries[1].refreshed is True
    assert service._decrypt(connection.access_token_encrypted) == "new-access"
    assert service._decrypt(connection.refresh_token_encrypted) == "rotated-refresh"
    assert connection.status == "connected"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_canva_api_request_uses_access_token_only_for_provider_request(monkeypatch):
    service = CanvaService()
    seen = {}

    async def access_token(db, user_id):
        return "server-only-access-token"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, *, headers, json):
            seen.update(method=method, url=url, headers=headers)
            return FakeResponse({"dataset": {}})

    monkeypatch.setattr(service, "access_token", access_token)
    monkeypatch.setattr(canva_module.httpx, "AsyncClient", FakeAsyncClient)

    result = await service.api_request(FakeDb(None), uuid4(), "GET", "/brand-templates/test/dataset")

    assert result == {"dataset": {}}
    assert seen["headers"]["Authorization"] == "Bearer server-only-access-token"
    assert seen["url"].endswith("/brand-templates/test/dataset")
