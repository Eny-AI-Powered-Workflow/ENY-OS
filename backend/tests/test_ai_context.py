# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_ai_context.py
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

import pytest

from app.api.v1.endpoints.ai import (
    ChatRequest,
    build_context_prompt,
    get_recent_messages,
    prepare_ai_chat_context,
)


@pytest.mark.asyncio
async def test_ai_chat_omits_crm_data_without_leads_or_pipeline_permissions(monkeypatch):
    current_user = SimpleNamespace(id="user-1", display_name="Taylor")
    db = MagicMock()
    monkeypatch.setattr("app.api.v1.endpoints.ai.get_user_roles", lambda *_: ["marketing"])
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.get_optional_permissions_with_audit",
        MagicMock(return_value=set()),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.retrieve_knowledge",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.get_ai_platform_context",
        MagicMock(return_value={"active_knowledge_document_count": 1}),
    )
    ghl_context = AsyncMock()
    monkeypatch.setattr("app.api.v1.endpoints.ai.ghl_service.get_ai_context", ghl_context)

    roles, context_scopes, crm, _, platform = await prepare_ai_chat_context(
        ChatRequest(prompt="How many SOPs are available?"),
        current_user,
        db,
        "/api/v1/ai/chat",
    )

    assert roles == ["marketing"]
    assert context_scopes == {"role:marketing"}
    assert crm == {}
    assert platform["active_knowledge_document_count"] == 1
    ghl_context.assert_not_awaited()


@pytest.mark.asyncio
async def test_ai_chat_requests_pipeline_without_contacts_when_only_pipeline_is_authorized(monkeypatch):
    current_user = SimpleNamespace(id="user-2", display_name="Morgan")
    db = MagicMock()
    monkeypatch.setattr("app.api.v1.endpoints.ai.get_user_roles", lambda *_: ["programs_manager"])
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.get_optional_permissions_with_audit",
        MagicMock(return_value={"pipeline:read"}),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.retrieve_knowledge",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.get_ai_platform_context",
        MagicMock(return_value={"active_knowledge_document_count": 0}),
    )
    ghl_context = AsyncMock(return_value={"pipeline": {"total_leads": 0}})
    monkeypatch.setattr("app.api.v1.endpoints.ai.ghl_service.get_ai_context", ghl_context)

    await prepare_ai_chat_context(
        ChatRequest(prompt="Summarize pipeline health."),
        current_user,
        db,
        "/api/v1/ai/chat",
    )

    ghl_context.assert_awaited_once_with(include_contacts=False, include_pipeline=True)


def test_context_prompt_personalizes_and_uses_inventory_instead_of_search_hit_count():
    prompt = build_context_prompt(
        "How many SOPs are here?",
        {},
        [],
        display_name="Taylor",
        roles=["ceo"],
        platform_context={
            "active_knowledge_document_count": 6,
            "active_knowledge_documents": [
                {"title": "ENY Executive Operating Principles", "department": "ceo"}
            ],
            "department_member_counts": [{"department": "enrollment", "member_count": 4}],
        },
    )

    assert '"signed_in_user": "Taylor"' in prompt
    assert '"authorized_roles": ["ceo"]' in prompt
    assert '"active_knowledge_document_count": 6' in prompt
    assert "search returning no matching passages does not mean the library is empty" in prompt
    assert "authorized CRM context was retrieved" not in prompt


def test_conversation_history_hides_assistant_replies_outside_current_permissions():
    messages = [
        SimpleNamespace(role="assistant", content="Marketing-only answer", context_scopes=["role:marketing"]),
        SimpleNamespace(
            role="assistant",
            content="Contact-backed answer",
            context_scopes=["leads:read", "pipeline:read", "role:marketing"],
        ),
        SimpleNamespace(role="user", content="What do I need to know?", context_scopes=[]),
    ]
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = messages

    visible = get_recent_messages(
        UUID("00000000-0000-0000-0000-000000000001"),
        db,
        allowed_context_scopes={"role:marketing"},
    )

    assert [message.content for message in visible] == [
        "What do I need to know?",
        "Marketing-only answer",
    ]
