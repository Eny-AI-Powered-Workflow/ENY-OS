# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/design_asset_service.py

from typing import AsyncIterator
from urllib.parse import quote
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile

from app.core.config import settings


class DesignAssetService:
    allowed_mime_types = {
        "image/png", "image/jpeg", "image/webp", "application/pdf", "video/mp4",
    }
    file_extensions = {
        "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp",
        "application/pdf": "pdf", "video/mp4": "mp4",
    }

    def _headers(self) -> dict[str, str]:
        service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        if not service_key:
            raise HTTPException(status_code=503, detail="Private design asset storage is not configured")
        return {"apikey": service_key, "Authorization": f"Bearer {service_key}"}

    def _object_url(self, storage_path: str) -> str:
        bucket = quote(settings.SUPABASE_DESIGN_ASSET_BUCKET, safe="")
        path = quote(storage_path, safe="/")
        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}/{path}"

    async def upload(self, upload: UploadFile, size_bytes: int, audience: str) -> str:
        mime_type = upload.content_type or "application/octet-stream"
        if mime_type not in self.allowed_mime_types:
            raise HTTPException(status_code=415, detail="Supported files are PNG, JPEG, WebP, PDF, and MP4")
        max_size = settings.DESIGN_ASSET_MAX_UPLOAD_MB * 1024 * 1024
        if size_bytes <= 0 or size_bytes > max_size:
            raise HTTPException(status_code=413, detail=f"File exceeds the {settings.DESIGN_ASSET_MAX_UPLOAD_MB} MB upload limit")
        upload.file.seek(0)
        header = upload.file.read(16)
        upload.file.seek(0)
        signatures = {
            "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": header.startswith(b"\xff\xd8\xff"),
            "image/webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
            "application/pdf": header.startswith(b"%PDF-"),
            "video/mp4": len(header) >= 8 and header[4:8] == b"ftyp",
        }
        if not signatures.get(mime_type, False):
            raise HTTPException(status_code=415, detail="File content does not match its declared media type")
        extension = self.file_extensions[mime_type]
        storage_path = f"{audience}/{uuid4()}.{extension}"
        upload.file.seek(0)

        async def chunks() -> AsyncIterator[bytes]:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk

        headers = {
            **self._headers(),
            "Content-Type": mime_type,
            "Content-Length": str(size_bytes),
            "x-upsert": "false",
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(self._object_url(storage_path), headers=headers, content=chunks())
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Private design asset upload failed") from exc
        return storage_path

    async def create_signed_url(self, storage_path: str, expires_seconds: int = 900) -> str:
        bucket = quote(settings.SUPABASE_DESIGN_ASSET_BUCKET, safe="")
        path = quote(storage_path, safe="/")
        signed_object_url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/sign/{bucket}/{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    signed_object_url,
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json={"expiresIn": expires_seconds},
                )
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Unable to create a private asset preview link") from exc
        signed_url = result.get("signedURL") or result.get("signedUrl")
        if not signed_url:
            raise HTTPException(status_code=502, detail="Storage provider returned no signed preview URL")
        if signed_url.startswith("http://") or signed_url.startswith("https://"):
            return signed_url
        if not signed_url.startswith("/"):
            signed_url = f"/{signed_url}"
        return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1{signed_url}"


design_asset_service = DesignAssetService()
