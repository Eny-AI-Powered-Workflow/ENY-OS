import os
from types import SimpleNamespace

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

import pytest

from app.core.config import settings
from app.services.google_chat_service import GoogleChatService


@pytest.mark.asyncio
async def test_google_chat_service_reports_when_webhook_is_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CHAT_SALES_WEBHOOK_URL", "")

    result = await GoogleChatService().send_message("A sales alert")

    assert result == {"status": "not_configured"}


@pytest.mark.asyncio
async def test_google_chat_service_posts_message_to_configured_webhook(monkeypatch):
    monkeypatch.setattr(
        settings,
        "GOOGLE_CHAT_SALES_WEBHOOK_URL",
        "https://chat.example.test/webhook",
    )
    requests = []

    class Response:
        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, timeout):
            assert timeout == 10.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            requests.append((url, json))
            return Response()

    monkeypatch.setattr("app.services.google_chat_service.httpx.AsyncClient", Client)

    result = await GoogleChatService().send_message("A sales alert")

    assert result == {"status": "sent"}
    assert requests == [
        ("https://chat.example.test/webhook", {"text": "A sales alert"}),
    ]
