# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_videographer_workflow.py
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.deps import require_permission
from app.api.v1.endpoints.videographer import router
from app.models.audit_log import AuditLog
from app.models.operational_alert import OperationalAlert
from app.services.videographer_service import VideographerService


def test_clip_normalization_rejects_invalid_timestamps():
    service = VideographerService()

    assert service._normalize_clip({"title": "Too long", "start_seconds": 8, "end_seconds": 12}, 10) is None
    assert service._normalize_clip({"title": "Invalid", "start_seconds": 4, "end_seconds": 4}, 10) is None
    clip = service._normalize_clip({"title": "Valid", "start_seconds": 1, "end_seconds": 4}, 10)
    assert clip is not None
    assert clip["status"] == "draft"
    assert clip["kind"] == "short_form_clip"


def test_generated_output_flags_caption_and_brand_issues():
    service = VideographerService()

    clip = service._normalize_clip({
        "title": "Clip",
        "start_seconds": 0,
        "end_seconds": 4,
        "caption": " ",
        "brand_consistent": False,
        "brand_issues": ["Uses an unapproved claim"],
    }, 8)

    assert clip is not None
    assert clip["caption_quality_issues"] == ["missing"]
    assert clip["brand_consistent"] is False
    assert clip["brand_issues"] == ["Uses an unapproved claim"]


def test_publish_route_requires_video_publish_permission():
    publish_route = next(
        route for route in router.routes
        if getattr(route, "path", "").endswith("/outputs/{output_index}/publish")
    )
    scopes = {
        cell.cell_contents
        for dependency in publish_route.dependant.dependencies
        for cell in (dependency.call.__closure__ or ())
        if isinstance(cell.cell_contents, str)
    }

    assert "video:publish" in scopes


def test_video_routes_declare_expected_permission_scopes():
    expected = [
        ("GET", "/assets", "video:read"),
        ("POST", "/assets", "video:upload"),
        ("POST", "/assets/{asset_id}/transcribe", "video:edit"),
        ("POST", "/assets/{asset_id}/generate-clips", "video:edit"),
        ("POST", "/assets/{asset_id}/outputs/{output_index}/review", "video:approve"),
        ("POST", "/assets/{asset_id}/outputs/{output_index}/publish", "video:publish"),
    ]
    registered = {(frozenset(route.methods), route.path): route for route in router.routes if hasattr(route, "dependant")}

    for method, path, required_scope in expected:
        route = registered[(frozenset({method}), path)]
        scopes = {
            cell.cell_contents
            for dependency in route.dependant.dependencies
            for cell in (dependency.call.__closure__ or ())
            if isinstance(cell.cell_contents, str)
        }
        assert required_scope in scopes


def test_denied_permission_attempt_is_written_to_audit_log():
    query = Mock()
    query.join.return_value = query
    query.filter.return_value = query
    query.first.return_value = None
    database = Mock()
    database.query.return_value = query
    current_user = SimpleNamespace(id=uuid4())
    checker = require_permission("video:publish")

    with pytest.raises(HTTPException) as error:
        checker(current_user, database)

    assert error.value.status_code == 403
    audit = database.add.call_args.args[0]
    assert isinstance(audit, AuditLog)
    assert audit.user_id == current_user.id
    assert audit.permission_scope == "video:publish"
    assert audit.granted is False
    database.commit.assert_called_once()


def test_user_can_read_own_team_and_other_department_access_is_audited(monkeypatch):
    service = VideographerService()
    user_id = uuid4()
    video_asset = SimpleNamespace(id=uuid4(), team="videographer")
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = video_asset
    database = Mock()
    database.query.return_value = query
    monkeypatch.setattr(service, "allowed_teams", lambda _db, _user_id: {"videographer"})

    assert service.get_asset(database, video_asset.id, user_id) is video_asset
    granted_audit = database.add.call_args.args[0]
    assert isinstance(granted_audit, AuditLog)
    assert granted_audit.permission_scope == "video:team:read:videographer"
    assert granted_audit.granted is True

    video_asset.team = "marketing"
    with pytest.raises(HTTPException) as error:
        service.get_asset(database, video_asset.id, user_id)

    assert error.value.status_code == 404
    denied_audit = database.add.call_args.args[0]
    assert denied_audit.permission_scope == "video:team:read:marketing"
    assert denied_audit.granted is False


def test_asset_list_applies_owner_team_and_audience_filters(monkeypatch):
    service = VideographerService()
    user_id = uuid4()
    owner_id = uuid4()
    assets = [SimpleNamespace(id=uuid4())]
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = assets
    database = Mock()
    database.query.return_value = query
    monkeypatch.setattr(service, "allowed_teams", lambda _db, _user_id: {"videographer"})

    result = service.list_assets(
        database, user_id=user_id, owner_id=owner_id, team="videographer", audience="marketing"
    )

    assert result == assets
    assert query.filter.call_count == 4


@pytest.mark.asyncio
async def test_upload_to_other_department_is_denied_and_audited(monkeypatch):
    service = VideographerService()
    user = SimpleNamespace(id=uuid4())
    database = Mock()
    monkeypatch.setattr(service, "allowed_teams", lambda _db, _user_id: {"videographer"})
    storage_upload = AsyncMock()
    monkeypatch.setattr("app.services.videographer_service.marketing_video_service.store_upload", storage_upload)

    with pytest.raises(HTTPException) as error:
        await service.upload(database, user, SimpleNamespace(), "Marketing asset", "marketing", "marketing")

    assert error.value.status_code == 403
    audit = database.add.call_args.args[0]
    assert isinstance(audit, AuditLog)
    assert audit.permission_scope == "video:team:upload:marketing"
    assert audit.granted is False
    storage_upload.assert_not_awaited()
    database.commit.assert_called_once()


@pytest.mark.asyncio
async def test_user_uploads_video_under_own_team(monkeypatch):
    service = VideographerService()
    user_id = uuid4()
    current_user = SimpleNamespace(id=user_id)
    upload = SimpleNamespace(
        file=BytesIO(b"video"),
        filename="recording.mp4",
        content_type="video/mp4",
        read=AsyncMock(return_value=b""),
    )
    database = Mock()
    monkeypatch.setattr(service, "allowed_teams", lambda _db, _user_id: {"videographer"})
    monkeypatch.setattr(
        "app.services.videographer_service.marketing_video_service.store_upload",
        AsyncMock(return_value="private/recording.mp4"),
    )

    asset = await service.upload(database, current_user, upload, "Studio recording", "videographer", "marketing")

    assert asset.created_by == user_id
    assert asset.team == "videographer"
    assert asset.audience == "marketing"
    assert database.commit.called


@pytest.mark.asyncio
async def test_end_to_end_upload_transcribe_generate_review_publish(monkeypatch):
    service = VideographerService()
    user_id = uuid4()
    current_user = SimpleNamespace(id=user_id)
    database = Mock()
    alert_query = Mock()
    alert_query.filter.return_value = alert_query
    alert_query.first.return_value = None
    database.query.return_value = alert_query
    upload = SimpleNamespace(
        file=BytesIO(b"video"), filename="recording.mp4", content_type="video/mp4",
    )
    monkeypatch.setattr(service, "allowed_teams", lambda _db, _user_id: {"videographer"})
    monkeypatch.setattr(
        "app.services.videographer_service.marketing_video_service.store_upload",
        AsyncMock(return_value="private/recording.mp4"),
    )
    asset = await service.upload(database, current_user, upload, "Studio recording", "videographer", "marketing")
    asset.id = uuid4()
    monkeypatch.setattr(service, "get_asset", lambda _db, _asset_id, _user_id: asset)
    monkeypatch.setattr(
        "app.services.videographer_service.marketing_video_service.transcribe",
        AsyncMock(return_value={
            "status": "transcribed", "text": "A source transcript", "duration": 20,
            "segments": [{"start": 1, "end": 5, "text": "A source transcript"}],
            "provider": "OpenAI Whisper",
        }),
    )
    monkeypatch.setattr("app.services.videographer_service.retrieve_knowledge", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        "app.services.videographer_service.ClaudeService",
        lambda: SimpleNamespace(invoke=AsyncMock(return_value=json.dumps({"clips": [{
            "title": "Source clip", "start_seconds": 1, "end_seconds": 5,
            "caption": "Approved source caption", "hook": "Source hook",
            "brand_consistent": True, "brand_issues": [],
        }]}))),
    )

    transcript = await service.transcribe(database, asset.id, current_user)
    generated = await service.generate_clips(database, asset.id, current_user)
    reviewed = service.review_output(database, asset.id, 0, "approved", "Verified source and caption", current_user)
    monkeypatch.setattr(
        "app.services.videographer_service.marketing_video_service.create_signed_url",
        AsyncMock(return_value="https://storage.example/signed"),
    )
    publish_call = AsyncMock(return_value={"status": "success", "published": True, "url": "https://channel.example/video"})
    monkeypatch.setattr(
        "app.services.videographer_service.N8NService",
        lambda: SimpleNamespace(trigger_workflow=publish_call),
    )
    published = await service.publish_output(database, asset.id, 0, "instagram", current_user)

    assert transcript["transcript"] == "A source transcript"
    assert generated["clips"][0]["status"] == "draft"
    assert reviewed["clip"]["status"] == "approved"
    assert published["clip"]["status"] == "published"
    assert published["clip"]["published_url"] == "https://channel.example/video"
    publish_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_transcription_failure_creates_operational_alert(monkeypatch):
    service = VideographerService()
    user = SimpleNamespace(id=uuid4())
    asset = SimpleNamespace(
        id=uuid4(), title="Recording", original_filename="recording.mp4", mime_type="video/mp4",
        size_bytes=5, storage_path="private/recording.mp4", team="videographer", audience="marketing",
        created_by=user.id, transcript=None, duration_seconds=None, transcript_segments=[],
        transcript_provider=None, generated_outputs=[], created_at=None, status="uploaded",
    )
    database = Mock()
    alert_query = Mock()
    alert_query.filter.return_value = alert_query
    alert_query.first.return_value = None
    database.query.return_value = alert_query
    monkeypatch.setattr(service, "get_asset", lambda *_: asset)
    monkeypatch.setattr(
        "app.services.videographer_service.marketing_video_service.transcribe",
        AsyncMock(return_value={"status": "not_configured", "message": "Whisper key missing"}),
    )

    result = await service.transcribe(database, asset.id, user)

    assert result["transcription"]["status"] == "not_configured"
    alerts = [call.args[0] for call in database.add.call_args_list if isinstance(call.args[0], OperationalAlert)]
    assert alerts and alerts[0].alert_type == "video_transcription_failed"
    database.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generated_caption_and_brand_failures_create_alerts(monkeypatch):
    service = VideographerService()
    user = SimpleNamespace(id=uuid4())
    asset = SimpleNamespace(
        id=uuid4(), title="Recording", team="videographer", storage_path="private/recording.mp4",
        transcript="Source", transcript_segments=[], duration_seconds=20, generated_outputs=[], status="transcribed",
    )
    database = Mock()
    alert_query = Mock()
    alert_query.filter.return_value = alert_query
    alert_query.first.return_value = None
    database.query.return_value = alert_query
    monkeypatch.setattr(service, "get_asset", lambda *_: asset)
    monkeypatch.setattr("app.services.videographer_service.retrieve_knowledge", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        "app.services.videographer_service.ClaudeService",
        lambda: SimpleNamespace(invoke=AsyncMock(return_value=json.dumps({"clips": [{
            "title": "Weak output", "start_seconds": 1, "end_seconds": 5,
            "caption": "", "brand_consistent": False, "brand_issues": ["Wrong claim"],
        }]}))),
    )

    result = await service.generate_clips(database, asset.id, user)

    assert result["clips"][0]["caption_quality_issues"] == ["missing"]
    alert_types = {
        call.args[0].alert_type for call in database.add.call_args_list
        if isinstance(call.args[0], OperationalAlert)
    }
    assert alert_types == {"video_caption_quality", "video_branding_review"}
    database.commit.assert_called_once()


@pytest.mark.asyncio
async def test_clip_generation_failure_creates_operational_alert(monkeypatch):
    service = VideographerService()
    user = SimpleNamespace(id=uuid4())
    asset = SimpleNamespace(
        id=uuid4(), title="Recording", team="videographer", storage_path="private/recording.mp4",
        transcript="Source", transcript_segments=[], duration_seconds=20, generated_outputs=[], status="transcribed",
    )
    database = Mock()
    alert_query = Mock()
    alert_query.filter.return_value = alert_query
    alert_query.first.return_value = None
    database.query.return_value = alert_query
    monkeypatch.setattr(service, "get_asset", lambda *_: asset)
    monkeypatch.setattr("app.services.videographer_service.retrieve_knowledge", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        "app.services.videographer_service.ClaudeService",
        lambda: SimpleNamespace(invoke=AsyncMock(side_effect=RuntimeError("Provider unavailable"))),
    )

    with pytest.raises(HTTPException) as error:
        await service.generate_clips(database, asset.id, user)

    assert error.value.status_code == 502
    alerts = [call.args[0] for call in database.add.call_args_list if isinstance(call.args[0], OperationalAlert)]
    assert alerts and alerts[0].alert_type == "video_clip_generation_failed"
    database.commit.assert_called_once()


@pytest.mark.asyncio
async def test_publish_requires_approved_output(monkeypatch):
    service = VideographerService()
    asset = SimpleNamespace(id=uuid4(), generated_outputs=[{"status": "draft"}], status="ready_for_review")
    database = Mock()
    alert_query = Mock()
    alert_query.filter.return_value = alert_query
    alert_query.first.return_value = None
    database.query.return_value = alert_query
    monkeypatch.setattr(service, "get_asset", lambda *_: asset)
    trigger = AsyncMock()
    monkeypatch.setattr("app.services.videographer_service.N8NService", lambda: SimpleNamespace(trigger_workflow=trigger))

    with pytest.raises(HTTPException) as error:
        await service.publish_output(database, asset.id, 0, "instagram", SimpleNamespace(id=uuid4()))

    assert error.value.status_code == 409
    trigger.assert_not_awaited()

    assert any(isinstance(call.args[0], OperationalAlert) for call in database.add.call_args_list)
    database.commit.assert_called_once()


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
    alert_query = Mock()
    alert_query.filter.return_value = alert_query
    alert_query.first.return_value = None
    database.query.return_value = alert_query
    monkeypatch.setattr(service, "get_asset", lambda *_: asset)
    monkeypatch.setattr("app.services.videographer_service.marketing_video_service.create_signed_url", AsyncMock(return_value="https://storage.example/signed"))
    trigger = AsyncMock(return_value={"status": "error", "published": False, "message": "Publisher is not configured"})
    monkeypatch.setattr("app.services.videographer_service.N8NService", lambda: SimpleNamespace(trigger_workflow=trigger))

    with pytest.raises(HTTPException) as error:
        await service.publish_output(database, asset.id, 0, "instagram", SimpleNamespace(id=uuid4()))

    assert error.value.status_code == 502
    assert asset.generated_outputs[0]["status"] == "approved"
    assert asset.status == "approved"
    assert any(isinstance(call.args[0], OperationalAlert) for call in database.add.call_args_list)
    database.commit.assert_called_once()