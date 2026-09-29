# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_videographer_workflow.py
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.videographer_service import VideographerService


def test_clip_normalization_rejects_invalid_timestamps():
    service = VideographerService()

    assert service._normalize_clip({"title": "Too long", "start_seconds": 8, "end_seconds": 12}, 10) is None
    assert service._normalize_clip({"title": "Invalid", "start_seconds": 4, "end_seconds": 4}, 10) is None
    clip = service._normalize_clip({"title": "Valid", "start_seconds": 1, "end_seconds": 4}, 10)
    assert clip is not None
    assert clip["status"] == "draft"
    assert clip["kind"] == "short_form_clip"


@pytest.mark.asyncio
async def test_publish_requires_approved_output(monkeypatch):
    service = VideographerService()
    asset = SimpleNamespace(id=uuid4(), generated_outputs=[{"status": "draft"}], status="ready_for_review")
    monkeypatch.setattr(service, "get_asset", lambda *_: asset)
    trigger = AsyncMock()
    monkeypatch.setattr("app.services.videographer_service.N8NService", lambda: SimpleNamespace(trigger_workflow=trigger))

    with pytest.raises(HTTPException) as error:
        await service.publish_output(Mock(), asset.id, 0, "instagram", SimpleNamespace(id=uuid4()))

    assert error.value.status_code == 409
    trigger.assert_not_awaited()


@pytest.mark.asyncio
async def test_unconfirmed_n8n_publish_does_not_mark_clip_published(monkeypatch):
    service = VideographerService()
    asset = SimpleNamespace(
        id=uuid4(),
        storage_path="private/source.mp4",
        generated_outputs=[{"title": "Approved clip", "caption": "Copy", "start_seconds": 1, "end_seconds": 4, "status": "approved"}],
        status="approved",
    )
    database = Mock()
    monkeypatch.setattr(service, "get_asset", lambda *_: asset)
    monkeypatch.setattr("app.services.videographer_service.marketing_video_service.create_signed_url", AsyncMock(return_value="https://storage.example/signed"))
    trigger = AsyncMock(return_value={"status": "error", "published": False, "message": "Publisher is not configured"})
    monkeypatch.setattr("app.services.videographer_service.N8NService", lambda: SimpleNamespace(trigger_workflow=trigger))

    with pytest.raises(HTTPException) as error:
        await service.publish_output(database, asset.id, 0, "instagram", SimpleNamespace(id=uuid4()))

    assert error.value.status_code == 502
    assert asset.generated_outputs[0]["status"] == "approved"
    assert asset.status == "approved"
    database.commit.assert_not_called()