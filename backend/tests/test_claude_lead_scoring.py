# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_claude_lead_scoring.py
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

import pytest

from app.services.claude_service import ClaudeService


@pytest.mark.asyncio
async def test_claude_score_contract_weights_components_and_derives_hot_category():
    payload = {
        "intent_score": 100,
        "fit_score": 50,
        "engagement_score": 100,
        "reasoning": "The lead explicitly requested a consultation and attended a session.",
        "evidence": ["Consultation request", "Session attendance"],
        "unknowns": ["Budget"],
        "next_best_action": "Confirm budget and book a consultation.",
    }
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(payload))])
    service = ClaudeService.__new__(ClaudeService)
    service.async_client = SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(return_value=response)))
    service.model = "test-model"
    service._system_prompt = lambda role_context: "Sales scoring test"

    result = await service.score_lead({"id": "contact-1", "source": "webinar"})

    assert result["score"] == 85
    assert result["category"] == "hot"
    assert result["score_origin"] == "claude"
    assert result["score_factors"] == {
        "intent_score": 100,
        "fit_score": 50,
        "engagement_score": 100,
    }
    assert result["next_best_action"] == payload["next_best_action"]


@pytest.mark.asyncio
async def test_claude_score_contract_rejects_missing_component_scores():
    payload = {
        "intent_score": 100,
        "fit_score": 50,
        "reasoning": "Insufficient component scores.",
        "evidence": [],
        "unknowns": [],
        "next_best_action": "Request more information.",
    }
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(payload))])
    service = ClaudeService.__new__(ClaudeService)
    service.async_client = SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(return_value=response)))
    service.model = "test-model"
    service._system_prompt = lambda role_context: "Sales scoring test"

    with pytest.raises(ValueError, match="engagement_score"):
        await service.score_lead({"id": "contact-1"})


@pytest.mark.asyncio
async def test_claude_creative_assessment_uses_structured_tool_input_with_image():
    assessment = {
        "overall_score": 85,
        "verdict": "ready",
        "summary": "Clear and focused.",
        "strengths": [],
        "risks": [],
        "criteria": [{"name": "Clarity", "score": 85, "feedback": "Clear."}],
        "recommendations": [],
        "accessibility_checks": [],
        "evidence": [],
    }
    response = SimpleNamespace(content=[
        SimpleNamespace(
            type="tool_use",
            name="submit_creative_assessment",
            input=assessment,
        ),
    ])
    create = AsyncMock(return_value=response)
    service = ClaudeService.__new__(ClaudeService)
    service.async_client = SimpleNamespace(messages=SimpleNamespace(create=create))
    service.model = "test-model"
    service._system_prompt = lambda role_context: "Creative assessment test"

    result = await service.assess_creative(
        prompt="Assess the design",
        image_base64="cG5n",
        media_type="image/png",
        role_context="marketing creative review",
    )

    assert result == assessment
    assert create.await_args.kwargs["messages"][0]["content"] == [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": "cG5n"},
        },
        {"type": "text", "text": "Assess the design"},
    ]
    assert create.await_args.kwargs["tool_choice"] == {
        "type": "tool",
        "name": "submit_creative_assessment",
    }


@pytest.mark.asyncio
async def test_claude_creative_assessment_rejects_response_without_tool_result():
    response = SimpleNamespace(content=[SimpleNamespace(type="text", text="I cannot assess this.")])
    service = ClaudeService.__new__(ClaudeService)
    service.async_client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=response)),
    )
    service.model = "test-model"
    service._system_prompt = lambda role_context: "Creative assessment test"

    with pytest.raises(ValueError, match="structured creative assessment"):
        await service.assess_creative(prompt="Assess the design")
