# C:\Users\Melody\Documents\ENY-OS\backend\app\services\signaturely_service.py
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings


class SignaturelyService:
    """Read contract status from Signaturely without storing document data locally."""

    async def list_documents(self, page: int, limit: int) -> dict[str, Any]:
        if not settings.SIGNATURELY_API_KEY:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "signaturely"},
            )

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{settings.SIGNATURELY_API_BASE_URL.rstrip('/')}/api/v1/documents",
                    params={"page": page, "limit": limit},
                    headers={"Authorization": f"Api-Key {settings.SIGNATURELY_API_KEY}"},
                )
                response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise HTTPException(status_code=503, detail="Signaturely rate limit reached; retry later") from exc
            if exc.response.status_code in {401, 403}:
                raise HTTPException(
                    status_code=503,
                    detail={"code": "provider_auth_failed", "provider": "signaturely"},
                ) from exc
            raise HTTPException(status_code=502, detail="Signaturely contract status is unavailable") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Signaturely is unavailable or returned an invalid response") from exc

        records = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            raise HTTPException(status_code=502, detail="Signaturely returned an invalid documents response")

        documents = []
        for record in records:
            if not isinstance(record, dict) or not record.get("id"):
                continue
            created_at = record.get("createdAt")
            updated_at = record.get("updatedAt")
            documents.append({
                "id": str(record["id"]),
                "title": str(record.get("title") or "Untitled document")[:200],
                "status": str(record.get("status") or "unknown")[:40],
                "created_at": created_at if isinstance(created_at, str) else None,
                "updated_at": updated_at if isinstance(updated_at, str) else None,
                "type": str(record.get("type") or "unknown")[:40],
            })

        total_pages = payload.get("totalPages")
        if not isinstance(total_pages, int) or isinstance(total_pages, bool):
            total_pages = None

        return {
            "provider": "signaturely",
            "documents": documents,
            "page": page,
            "limit": limit,
            "total_items": payload.get("totalItems"),
            "total_pages": total_pages,
            "has_more": page < total_pages if total_pages is not None else len(documents) >= limit,
        }


signaturely_service = SignaturelyService()