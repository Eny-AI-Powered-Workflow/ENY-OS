# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_marketing_video_service.py
import httpx
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.marketing_video_service import MarketingVideoService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "body", "expected_detail"),
    [
        (
            400,
            {"error": {"message": "Invalid file format. Supported formats are audio."}},
            "Invalid file format",
        ),
        (
            401,
            {"error": {"message": "Incorrect API key provided."}},
            "Check OPENAI_API_KEY",
        ),
        (
            429,
            {"error": {"message": "You exceeded your current quota."}},
            "billing and limits",
        ),
    ],
)
async def test_whisper_errors_explain_provider_rejections_without_exposing_credentials(
    monkeypatch, status_code, body, expected_detail
):
    service = MarketingVideoService()
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai-secret")
    monkeypatch.setattr(settings, "OPENAI_TRANSCRIPTION_MODEL", "whisper-1")

    async def respond(_request):
        return httpx.Response(status_code, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(HTTPException) as error:
            await service._transcribe_audio(client, "recording.mp3", b"audio", "audio/mpeg")

    assert error.value.status_code == 502
    assert expected_detail in error.value.detail
    assert "test-openai-secret" not in error.value.detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model", "response_format", "payload"),
    [
        ("whisper-1", "verbose_json", {"text": "timestamped speech", "duration": 12.5, "segments": [{"start": 0, "end": 2}]}),
        ("gpt-transcribe", "json", {"text": "transcribed speech"}),
    ],
)
async def test_transcription_models_use_compatible_response_formats(
    monkeypatch, model, response_format, payload
):
    service = MarketingVideoService()
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai-secret")
    monkeypatch.setattr(settings, "OPENAI_TRANSCRIPTION_MODEL", model)
    requests = []

    async def respond(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await service._transcribe_audio(client, "recording.mp3", b"audio", "audio/mpeg")

    assert len(requests) == 1
    assert f'name="model"\r\n\r\n{model}'.encode() in requests[0].content
    assert f'name="response_format"\r\n\r\n{response_format}'.encode() in requests[0].content
    combined = service._transcript_result([result], [0])
    if model == "whisper-1":
        assert combined["provider"] == "OpenAI Whisper"
        assert combined["duration"] == 12.5
        assert combined["segments"][0]["start"] == 0
    else:
        assert combined["text"] == "transcribed speech"
        assert combined["duration"] is None
        assert combined["segments"] == []


@pytest.mark.asyncio
async def test_small_video_upload_is_prepared_as_audio_before_whisper(monkeypatch):
    service = MarketingVideoService()
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai-secret")
    monkeypatch.setattr(settings, "OPENAI_TRANSCRIPTION_MODEL", "whisper-1")
    prepared = {}

    async def transcribe_in_chunks(_client, _url, filename, mime_type):
        prepared.update(filename=filename, mime_type=mime_type)
        return {"status": "transcribed", "text": "speech"}

    monkeypatch.setattr(service, "_transcribe_in_chunks", transcribe_in_chunks)

    result = await service.transcribe(
        "private/recording.mp4",
        "recording.mp4",
        "video/mp4",
        1024,
    )

    assert result["text"] == "speech"
    assert prepared == {"filename": "recording.mp4", "mime_type": "video/mp4"}
