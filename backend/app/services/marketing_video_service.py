# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/marketing_video_service.py

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile

from app.core.config import settings


class MarketingVideoService:
    allowed_types = {
        "video/mp4", "video/webm", "video/quicktime",
        "audio/mpeg", "audio/mp4", "audio/wav", "audio/webm",
    }
    whisper_max_bytes = 25 * 1024 * 1024
    ffmpeg_input_extensions = {
        "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
        "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/wav": ".wav", "audio/webm": ".webm",
    }

    def _storage_headers(self) -> dict[str, str]:
        key = settings.SUPABASE_SERVICE_ROLE_KEY
        return {"apikey": key, "Authorization": f"Bearer {key}"}

    async def store_upload(self, upload: UploadFile, size_bytes: int) -> str:
        if upload.content_type not in self.allowed_types:
            raise HTTPException(status_code=415, detail="Upload an MP4, WebM, MOV, or supported audio file")
        max_bytes = settings.MARKETING_VIDEO_MAX_UPLOAD_MB * 1024 * 1024
        if size_bytes <= 0 or size_bytes > max_bytes:
            raise HTTPException(status_code=413, detail=f"Video upload exceeds the {settings.MARKETING_VIDEO_MAX_UPLOAD_MB} MB limit")
        if not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise HTTPException(status_code=503, detail="Private Marketing media storage is not configured")

        suffix = (upload.filename or "media").rsplit(".", 1)[-1].lower()
        storage_path = f"{uuid4()}.{suffix}" if "." in (upload.filename or "") else str(uuid4())
        bucket = quote(settings.SUPABASE_MARKETING_VIDEO_BUCKET, safe="")
        url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}/{quote(storage_path, safe='/')}"
        upload.file.seek(0)

        async def chunks():
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk

        headers = {
            **self._storage_headers(),
            "Content-Type": upload.content_type or "application/octet-stream",
            "Content-Length": str(size_bytes),
            "x-upsert": "false",
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(url, headers=headers, content=chunks())
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Private Marketing media upload failed") from exc
        return storage_path

    async def transcribe(self, storage_path: str, filename: str, mime_type: str, size_bytes: int) -> dict[str, Any]:
        if not settings.OPENAI_API_KEY:
            return {"status": "not_configured", "message": "Set OPENAI_API_KEY in the backend environment to enable Whisper transcription."}

        bucket = quote(settings.SUPABASE_MARKETING_VIDEO_BUCKET, safe="")
        url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}/{quote(storage_path, safe='/')}"
        async with httpx.AsyncClient(timeout=180.0) as client:
            if size_bytes <= self.whisper_max_bytes and mime_type != "video/quicktime":
                try:
                    media_response = await client.get(url, headers=self._storage_headers())
                    media_response.raise_for_status()
                except httpx.HTTPError as exc:
                    raise HTTPException(status_code=502, detail="Unable to read private Marketing media") from exc
                payload = await self._whisper(client, filename, media_response.content, mime_type)
                return self._transcript_result([payload], [0])

            return await self._transcribe_in_chunks(client, url, filename, mime_type)

    async def _whisper(self, client: httpx.AsyncClient, filename: str, content: bytes, mime_type: str) -> dict[str, Any]:
        try:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                data={"model": "whisper-1", "response_format": "verbose_json"},
                files={"file": (filename, content, mime_type)},
                timeout=180.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Whisper transcription failed") from exc

    async def _transcribe_in_chunks(self, client: httpx.AsyncClient, url: str, filename: str, mime_type: str) -> dict[str, Any]:
        extension = self.ffmpeg_input_extensions.get(mime_type)
        if not extension:
            return {"status": "unsupported_format", "message": "This media format cannot be prepared for transcription."}
        try:
            with tempfile.TemporaryDirectory(prefix="eny-marketing-video-") as temporary_directory:
                directory = Path(temporary_directory)
                source_path = directory / f"source{extension}"
                try:
                    async with client.stream("GET", url, headers=self._storage_headers(), timeout=300.0) as response:
                        response.raise_for_status()
                        with source_path.open("wb") as source_file:
                            async for chunk in response.aiter_bytes(1024 * 1024):
                                source_file.write(chunk)
                except httpx.HTTPError as exc:
                    raise HTTPException(status_code=502, detail="Unable to read private Marketing media") from exc

                output_pattern = str(directory / "audio-%03d.mp3")
                process = await asyncio.create_subprocess_exec(
                    settings.FFMPEG_PATH, "-y", "-i", str(source_path), "-vn", "-ac", "1", "-ar", "16000",
                    "-b:a", "64k", "-f", "segment", "-segment_time", "600", "-reset_timestamps", "1", output_pattern,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
                )
                try:
                    _, stderr = await asyncio.wait_for(process.communicate(), timeout=1200.0)
                except asyncio.TimeoutError as exc:
                    process.kill()
                    await process.wait()
                    raise HTTPException(status_code=504, detail="Audio preparation timed out") from exc
                if process.returncode != 0:
                    logger_text = stderr.decode("utf-8", errors="replace")[-1000:]
                    raise HTTPException(status_code=422, detail=f"Audio preparation failed: {logger_text}")

                audio_chunks = sorted(directory.glob("audio-*.mp3"))
                if not audio_chunks:
                    raise HTTPException(status_code=422, detail="No audio track was found in the uploaded media")
                payloads = []
                offsets = []
                for index, audio_chunk in enumerate(audio_chunks):
                    content = audio_chunk.read_bytes()
                    if len(content) > self.whisper_max_bytes:
                        raise HTTPException(status_code=413, detail="Prepared audio chunk exceeds Whisper's 25 MB limit")
                    payloads.append(await self._whisper(client, f"{Path(filename).stem}-{index + 1}.mp3", content, "audio/mpeg"))
                    offsets.append(index * 600)
                return self._transcript_result(payloads, offsets)
        except FileNotFoundError as exc:
            return {"status": "not_configured", "message": "FFmpeg is required for recordings over 25 MB and QuickTime files. It is installed in the backend container."}

    @staticmethod
    def _transcript_result(payloads: list[dict[str, Any]], offsets: list[int]) -> dict[str, Any]:
        segments = []
        text_parts = []
        duration = 0.0
        for payload, offset in zip(payloads, offsets):
            if payload.get("text"):
                text_parts.append(str(payload["text"]))
            duration += float(payload.get("duration") or 0)
            for segment in payload.get("segments", []):
                segments.append({
                    **segment,
                    "start": float(segment.get("start", 0)) + offset,
                    "end": float(segment.get("end", 0)) + offset,
                })
        return {"status": "transcribed", "provider": "OpenAI Whisper", "text": "\n".join(text_parts), "duration": duration, "segments": segments}


marketing_video_service = MarketingVideoService()
