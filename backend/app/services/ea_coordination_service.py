# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/ea_coordination_service.py
import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings


class EACoordinationService:
    """Backend-only adapter for read-only Google Calendar and Tasks access."""

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0
        self._token_lock = asyncio.Lock()

    async def _get_access_token(self, client: httpx.AsyncClient) -> str | None:
        credentials = (
            settings.GOOGLE_OAUTH_CLIENT_ID,
            settings.GOOGLE_OAUTH_CLIENT_SECRET,
            settings.GOOGLE_OAUTH_REFRESH_TOKEN,
        )
        if not any(credentials):
            return None
        if not all(credentials):
            raise ValueError("google_oauth_configuration_incomplete")

        async with self._token_lock:
            if self._access_token and time.monotonic() < self._access_token_expires_at:
                return self._access_token

            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": credentials[0],
                    "client_secret": credentials[1],
                    "refresh_token": credentials[2],
                    "grant_type": "refresh_token",
                },
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError("google_oauth_refresh_failed") from exc
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
                raise ValueError("google_oauth_invalid_response")

            expires_in = payload.get("expires_in", 3600)
            if not isinstance(expires_in, (int, float)) or isinstance(expires_in, bool):
                raise ValueError("google_oauth_invalid_expiry")
            self._access_token = payload["access_token"]
            self._access_token_expires_at = time.monotonic() + max(0, expires_in - 60)
            return self._access_token

    async def _get_json(
        self,
        base_url: str,
        path: str,
        params: dict[str, str],
        provider: str,
    ) -> dict[str, Any]:
        if not all((
            settings.GOOGLE_OAUTH_CLIENT_ID,
            settings.GOOGLE_OAUTH_CLIENT_SECRET,
            settings.GOOGLE_OAUTH_REFRESH_TOKEN,
        )):
            if any((
                settings.GOOGLE_OAUTH_CLIENT_ID,
                settings.GOOGLE_OAUTH_CLIENT_SECRET,
                settings.GOOGLE_OAUTH_REFRESH_TOKEN,
            )):
                return {
                    "status": "error",
                    "items": [],
                    "confidence": "unavailable",
                    "error": "google_oauth_configuration_incomplete",
                }
            return {"status": "not_configured", "items": [], "confidence": "unavailable"}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                token = await self._get_access_token(client)
                if not token:
                    return {"status": "not_configured", "items": [], "confidence": "unavailable"}
                response = await client.get(
                    f"{base_url.rstrip('/')}/{path.lstrip('/')}",
                    params=params,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                error = f"{provider}_google_api_auth_failed"
            elif exc.response.status_code == 429:
                error = "google_api_rate_limited"
            else:
                error = "google_api_request_failed"
            return {"status": "error", "items": [], "confidence": "unavailable", "error": error}
        except httpx.HTTPError:
            return {
                "status": "error",
                "items": [],
                "confidence": "unavailable",
                "error": "provider_unavailable",
            }
        except ValueError as exc:
            error = str(exc) if str(exc).startswith("google_oauth_") else "provider_invalid_response"
            return {"status": "error", "items": [], "confidence": "unavailable", "error": error}

        if not isinstance(payload, dict) or not isinstance(payload.get("items", []), list):
            return {
                "status": "error",
                "items": [],
                "confidence": "unavailable",
                "error": "provider_invalid_response",
            }
        return {"status": "connected", "items": payload.get("items", []), "confidence": "high"}

    async def get_calendar(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        params = {
            "timeMin": now.isoformat(),
            "timeMax": (now + timedelta(days=30)).isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "100",
            "fields": "items(id,summary,start,end,status)",
        }
        return await self._get_json(
            settings.EA_CALENDAR_BASE_URL,
            settings.EA_CALENDAR_PATH,
            params,
            "calendar",
        )

    async def get_tasks(self) -> dict[str, Any]:
        params = {
            "maxResults": "100",
            "showCompleted": "false",
            "showHidden": "false",
            "fields": "items(id,title,due,status,updated)",
        }
        return await self._get_json(
            settings.EA_TASKS_BASE_URL,
            settings.EA_TASKS_PATH,
            params,
            "tasks",
        )

    async def get_coordination(self) -> dict[str, Any]:
        calendar, tasks = await asyncio.gather(self.get_calendar(), self.get_tasks())
        events = calendar.get("items", [])
        conflicts = []
        for index, event in enumerate(events):
            start = event.get("start", {})
            start_value = start.get("dateTime") or start.get("date") if isinstance(start, dict) else start
            for other in events[index + 1:]:
                other_start = other.get("start", {})
                other_start_value = (
                    other_start.get("dateTime") or other_start.get("date")
                    if isinstance(other_start, dict)
                    else other_start
                )
                if start_value and start_value == other_start_value:
                    conflicts.append({"first": event, "second": other})
        return {
            "calendar": calendar,
            "tasks": tasks,
            "conflicts": conflicts,
            "source": "google_calendar_and_tasks",
            "external_actions": "disabled",
        }


ea_coordination_service = EACoordinationService()
