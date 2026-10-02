import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

import httpx
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services import signaturely_service as signaturely_module
from app.services.signaturely_service import SignaturelyService


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://api.signaturely.com/api/v1/documents")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("provider error", request=request, response=response)

    def json(self):
        return self.payload


class FakeAsyncClient:
    response = None
    calls = []

    def __init__(self, *args, **kwargs):
        self.options = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs, self.options))
        return self.response


@pytest.mark.asyncio
async def test_signaturely_reads_status_with_api_key_and_minimal_fields(monkeypatch):
    FakeAsyncClient.response = FakeResponse({
        "data": [{
            "id": "contract-1",
            "title": "Enrollment agreement",
            "status": "completed",
            "type": "others",
            "createdAt": "2026-09-30T09:00:00Z",
            "updatedAt": "2026-10-01T10:00:00Z",
            "signers": [{"email": "private@example.com"}],
            "shareLink": "https://signaturely.example/signed",
            "originalFileUrl": "https://signaturely.example/private.pdf",
        }],
        "totalPages": 2,
        "totalItems": 26,
    })
    FakeAsyncClient.calls = []
    monkeypatch.setattr(signaturely_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "SIGNATURELY_API_KEY", "test-api-key")

    result = await SignaturelyService().list_documents(page=1, limit=25)

    assert result["provider"] == "signaturely"
    assert result["has_more"] is True
    assert result["documents"] == [{
        "id": "contract-1",
        "title": "Enrollment agreement",
        "status": "completed",
        "created_at": "2026-09-30T09:00:00Z",
        "updated_at": "2026-10-01T10:00:00Z",
        "type": "others",
    }]
    assert "private@example.com" not in repr(result)
    assert "shareLink" not in repr(result)
    url, request, options = FakeAsyncClient.calls[0]
    assert url.endswith("/api/v1/documents")
    assert request["params"] == {"page": 1, "limit": 25}
    assert request["headers"]["Authorization"] == "Api-Key test-api-key"
    assert options["timeout"] == 20.0


@pytest.mark.asyncio
async def test_signaturely_fails_closed_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "SIGNATURELY_API_KEY", "")

    with pytest.raises(HTTPException) as error:
        await SignaturelyService().list_documents(page=1, limit=25)

    assert error.value.status_code == 503
    assert error.value.detail == {"code": "provider_not_configured", "provider": "signaturely"}


@pytest.mark.asyncio
async def test_signaturely_rate_limits_are_retryable_service_unavailable(monkeypatch):
    FakeAsyncClient.response = FakeResponse({}, status_code=429)
    monkeypatch.setattr(signaturely_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "SIGNATURELY_API_KEY", "test-api-key")

    with pytest.raises(HTTPException) as error:
        await SignaturelyService().list_documents(page=1, limit=25)

    assert error.value.status_code == 503
    assert "rate limit" in error.value.detail.lower()