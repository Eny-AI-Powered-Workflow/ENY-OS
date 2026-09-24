# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/ea_coordination_service.py

from typing import Any

import httpx

from app.core.config import settings


class EACoordinationService:
    """Backend-only adapters for calendar and task providers."""

    async def _get_json(self, base_url: str, token: str, path: str) -> dict[str, Any]:
        if not base_url or not token:
            return {"status": "not_configured", "items": [], "confidence": "unavailable"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url.rstrip('/')}/{path.lstrip('/')}",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                    timeout=20.0,
                )
                response.raise_for_status()
                payload = response.json()
                items = payload.get("items", payload.get("events", payload.get("tasks", []))) if isinstance(payload, dict) else []
                return {"status": "connected", "items": items if isinstance(items, list) else [], "confidence": "high"}
        except Exception as exc:
            return {"status": "error", "items": [], "confidence": "unavailable", "error": str(exc)}

    async def get_calendar(self) -> dict[str, Any]:
        return await self._get_json(settings.EA_CALENDAR_BASE_URL, settings.EA_CALENDAR_TOKEN, settings.EA_CALENDAR_PATH)

    async def get_tasks(self) -> dict[str, Any]:
        return await self._get_json(settings.EA_TASKS_BASE_URL, settings.EA_TASKS_TOKEN, settings.EA_TASKS_PATH)


ea_coordination_service = EACoordinationService()
