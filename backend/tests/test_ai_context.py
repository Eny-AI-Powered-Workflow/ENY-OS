# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_ai_context.py
import os
import base64
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
from fastapi import HTTPException

from app.api.v1.endpoints.ai import (
    ChatRequest,
    DesignAssessmentRequest,
    _ai_proposable_workflows,
    assess_creative,
    build_context_prompt,
    get_assistant_integrations,
    get_recent_messages,
    prepare_ai_chat_context,
)


@pytest.mark.asyncio
async def test_ai_chat_omits_crm_data_without_leads_or_pipeline_permissions(monkeypatch):
    current_user = SimpleNamespace(id="user-1", display_name="Taylor")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        preferences={"focus_areas": ["leadership"]},
    )
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
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.ea_coordination_service.connection_status",
        lambda *_: {"connected": False},
    )
    ghl_context = AsyncMock()
    monkeypatch.setattr("app.api.v1.endpoints.ai.ghl_service.get_ai_context", ghl_context)

    roles, context_scopes, crm, _, platform, assistant_context = await prepare_ai_chat_context(
        ChatRequest(prompt="How many SOPs are available?"),
        current_user,
        db,
        "/api/v1/ai/chat",
    )

    assert roles == ["marketing"]
    assert context_scopes == {"role:marketing"}
    assert crm == {}
    assert platform["active_knowledge_document_count"] == 1
    assert assistant_context["timezone"] == "UTC"
    assert assistant_context["user_preferences"] == {"focus_areas": ["leadership"]}
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
        assistant_context={
            "timezone": "America/New_York",
            "user_local_time": "2026-10-20T09:00:00-04:00",
            "user_preferences": {"response_style": "concise"},
        },
    )

    assert '"signed_in_user": "Taylor"' in prompt
    assert '"authorized_roles": ["ceo"]' in prompt
    assert '"active_knowledge_document_count": 6' in prompt
    assert '"timezone": "America/New_York"' in prompt
    assert '"response_style": "concise"' in prompt
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


@pytest.mark.asyncio
async def test_creative_assessment_rejects_image_with_mismatched_media_type(monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.ai.get_user_roles", lambda *_: ["graphic_designer"])
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.get_optional_permissions_with_audit",
        MagicMock(return_value={"design:ai", "design:read_marketing"}),
    )
    request = DesignAssessmentRequest(
        title="Campaign concept",
        audience="marketing",
        channel="social",
        brief="A clear campaign concept with a concise message and visual direction.",
        image_base64=base64.b64encode(b"not a png").decode("ascii"),
        image_media_type="image/png",
    )

    with pytest.raises(HTTPException, match="image contents do not match"):
        await assess_creative(request, SimpleNamespace(id="designer-1"), MagicMock())


def test_ai_workflow_proposals_only_include_owned_draft_and_review_workflows():
    video_workflows = _ai_proposable_workflows(["videographer"])
    executive_workflows = _ai_proposable_workflows(["ceo"])

    assert video_workflows == []
    assert executive_workflows
    assert all(workflow["mode"] in {"shadow", "draft-only", "manual"} for _, workflow in executive_workflows)
    assert "eny-video-publish" not in {key for key, _ in executive_workflows}


def test_integration_catalog_reports_contacts_and_creative_access_separately():
    integrations = {
        item["id"]: item
        for item in get_assistant_integrations({"leads:read", "design:ai"})
    }

    assert integrations["gohighlevel"]["access"] == "contacts"
    assert integrations["creative_review"]["access"] == "approved_brand_and_design_standards"
    assert integrations["calendar"]["access"] == "no_access"


def test_integration_catalog_reports_shared_calendar_connection(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.endpoints.ai.ea_coordination_service.connection_status",
        lambda *_: {"connected": True},
    )

    integrations = get_assistant_integrations({"calendar:read"}, MagicMock())
    calendar = next(item for item in integrations if item["id"] == "calendar")

    assert calendar["status"] == "connected"
    assert calendar["access"] == "read"
