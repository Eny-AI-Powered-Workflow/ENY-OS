# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/ea_coordination_service.py
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.google_calendar import GoogleCalendarConnection, GoogleCalendarOAuthState


class EACoordinationService:
    """Backend adapter for shared, read-only Google Calendar and Tasks access."""

    CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"
    TASKS_SCOPE = "https://www.googleapis.com/auth/tasks.readonly"
    REQUIRED_SCOPES = (CALENDAR_SCOPE, TASKS_SCOPE)
    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    def configured(self) -> bool:
        return bool(
            settings.GOOGLE_OAUTH_CLIENT_ID
            and settings.GOOGLE_OAUTH_CLIENT_SECRET
            and settings.GOOGLE_CALENDAR_REDIRECT_URI
            and settings.GOOGLE_TOKEN_ENCRYPTION_KEY
        )

    def _redirect_uri(self) -> str:
        redirect_uri = settings.GOOGLE_CALENDAR_REDIRECT_URI.strip()
        parsed = urlsplit(redirect_uri)
        is_local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
        if (
            not parsed.hostname
            or (parsed.scheme != "https" and not is_local_http)
            or parsed.path != "/api/v1/calendar/oauth/callback"
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    "GOOGLE_CALENDAR_REDIRECT_URI must be the public HTTPS FastAPI callback URL "
                    "ending in /api/v1/calendar/oauth/callback. Register that exact URL in Google Cloud."
                ),
            )
        return redirect_uri

    def _fernet(self) -> Fernet:
        if not settings.GOOGLE_TOKEN_ENCRYPTION_KEY:
            raise HTTPException(status_code=503, detail="Google token encryption is not configured")
        try:
            return Fernet(settings.GOOGLE_TOKEN_ENCRYPTION_KEY.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="GOOGLE_TOKEN_ENCRYPTION_KEY must be a valid Fernet key",
            ) from exc

    def _encrypt(self, value: str) -> str:
        return self._fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def _decrypt(self, value: str) -> str:
        try:
            return self._fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Stored Google credentials could not be decrypted; reconnect Google Calendar",
            ) from exc

    def connection_status(self, db: Session) -> dict[str, Any]:
        """Report shared Google connection state without exposing stored tokens."""
        connection = (
            db.query(GoogleCalendarConnection)
            .filter(GoogleCalendarConnection.shared_slot == 1)
            .first()
        )
        return {
            "configured": self.configured(),
            "connected": bool(connection and connection.status == "connected"),
            "has_connection": connection is not None,
            "status": connection.status if connection else "not_connected",
            "connected_at": connection.connected_at.isoformat() if connection and connection.connected_at else None,
            "scopes": connection.scopes if connection else [],
        }

    def authorization_url(self, db: Session, user_id: Any, redirect_origin: str) -> str:
        """Create a one-time state record and Google consent URL for the shared account."""
        if not self.configured():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Configure Google OAuth client ID, client secret, callback URL, "
                    "and token encryption key before connecting Calendar"
                ),
            )
        redirect_uri = self._redirect_uri()
        state = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        db.query(GoogleCalendarOAuthState).filter(
            GoogleCalendarOAuthState.expires_at <= now
        ).delete(synchronize_session=False)
        db.add(GoogleCalendarOAuthState(
            state_hash=hashlib.sha256(state.encode("ascii")).hexdigest(),
            connected_by=user_id,
            redirect_origin=redirect_origin,
            expires_at=now + timedelta(minutes=10),
        ))
        db.commit()
        query = urlencode({
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.REQUIRED_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        })
        return f"{self.AUTHORIZE_URL}?{query}"

    def consume_denied_authorization(self, db: Session, state: str) -> str:
        """Consume Google's denied OAuth callback and return its previously approved origin."""
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        state_row = (
            db.query(GoogleCalendarOAuthState)
            .filter(GoogleCalendarOAuthState.state_hash == state_hash)
            .with_for_update()
            .first()
        )
        now = datetime.now(timezone.utc)
        if not state_row or state_row.used_at or state_row.expires_at <= now:
            raise HTTPException(status_code=400, detail="Google authorization state is invalid or expired")
        state_row.used_at = now
        redirect_origin = state_row.redirect_origin
        db.commit()
        return redirect_origin

    async def complete_authorization(self, db: Session, code: str, state: str) -> str:
        """Exchange Google's authorization code and persist the encrypted shared tokens."""
        if not self.configured():
            raise HTTPException(status_code=503, detail="Google Calendar OAuth is not configured")
        redirect_uri = self._redirect_uri()
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        state_row = (
            db.query(GoogleCalendarOAuthState)
            .filter(GoogleCalendarOAuthState.state_hash == state_hash)
            .with_for_update()
            .first()
        )
        now = datetime.now(timezone.utc)
        if not state_row or state_row.used_at or state_row.expires_at <= now:
            raise HTTPException(status_code=400, detail="Google authorization state is invalid, expired, or already used")

        connection = (
            db.query(GoogleCalendarConnection)
            .filter(GoogleCalendarConnection.shared_slot == 1)
            .with_for_update()
            .first()
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                    },
                )
                response.raise_for_status()
                tokens = response.json()
        except httpx.HTTPError as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail="Google authorization exchange failed") from exc

        if not isinstance(tokens, dict):
            db.rollback()
            raise HTTPException(status_code=502, detail="Google returned an invalid token response")
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        if not isinstance(access_token, str) or not access_token:
            db.rollback()
            raise HTTPException(status_code=502, detail="Google token response did not include an access token")
        if not isinstance(refresh_token, str) or not refresh_token:
            refresh_token = self._decrypt(connection.refresh_token_encrypted) if connection else None
        if not refresh_token:
            db.rollback()
            raise HTTPException(
                status_code=502,
                detail="Google did not return a refresh token; revoke app access in Google and connect again",
            )
        try:
            expires_in = int(tokens.get("expires_in") or 3600)
        except (TypeError, ValueError) as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail="Google token response had an invalid expiry") from exc
        if expires_in <= 0:
            db.rollback()
            raise HTTPException(status_code=502, detail="Google token response had an invalid expiry")

        returned_scopes = tokens.get("scope")
        scopes = returned_scopes.split() if isinstance(returned_scopes, str) else list(self.REQUIRED_SCOPES)
        if not set(self.REQUIRED_SCOPES).issubset(scopes):
            db.rollback()
            raise HTTPException(
                status_code=403,
                detail="Google Calendar and Tasks read-only access must both be approved",
            )

        values = {
            "access_token_encrypted": self._encrypt(access_token),
            "refresh_token_encrypted": self._encrypt(refresh_token),
            "token_expires_at": now + timedelta(seconds=expires_in),
            "scopes": scopes,
            "status": "connected",
            "connected_by": state_row.connected_by,
            "connected_at": now,
            "updated_at": now,
        }
        if connection:
            for name, value in values.items():
                setattr(connection, name, value)
        else:
            db.add(GoogleCalendarConnection(shared_slot=1, **values))
        state_row.used_at = now
        redirect_origin = state_row.redirect_origin
        db.commit()
        return redirect_origin

    async def _get_access_token(self, db: Session) -> str | None:
        """Refresh an expiring Google token server-side before Calendar or Tasks API access."""
        if not self.configured():
            raise ValueError("google_oauth_configuration_incomplete")

        connection = (
            db.query(GoogleCalendarConnection)
            .filter(GoogleCalendarConnection.shared_slot == 1)
            .first()
        )
        if not connection or connection.status != "connected":
            return None

        now = datetime.now(timezone.utc)
        expires_at = connection.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > now + timedelta(seconds=90):
            return self._decrypt(connection.access_token_encrypted)

        connection = (
            db.query(GoogleCalendarConnection)
            .filter(GoogleCalendarConnection.shared_slot == 1)
            .with_for_update()
            .populate_existing()
            .first()
        )
        if not connection or connection.status != "connected":
            db.rollback()
            return None
        now = datetime.now(timezone.utc)
        expires_at = connection.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > now + timedelta(seconds=90):
            access_token = self._decrypt(connection.access_token_encrypted)
            db.commit()
            return access_token

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                        "refresh_token": self._decrypt(connection.refresh_token_encrypted),
                        "grant_type": "refresh_token",
                    },
                )
                response.raise_for_status()
                tokens = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                connection.status = "error"
                db.commit()
            else:
                db.rollback()
            raise ValueError("google_oauth_refresh_failed") from exc
        except httpx.HTTPError as exc:
            db.rollback()
            raise ValueError("google_oauth_refresh_failed") from exc

        if not isinstance(tokens, dict) or not isinstance(tokens.get("access_token"), str) or not tokens["access_token"]:
            db.rollback()
            raise ValueError("google_oauth_invalid_response")
        try:
            expires_in = int(tokens.get("expires_in") or 3600)
        except (TypeError, ValueError) as exc:
            db.rollback()
            raise ValueError("google_oauth_invalid_expiry") from exc
        if expires_in <= 0:
            db.rollback()
            raise ValueError("google_oauth_invalid_expiry")

        connection.access_token_encrypted = self._encrypt(tokens["access_token"])
        refreshed_token = tokens.get("refresh_token")
        if isinstance(refreshed_token, str) and refreshed_token:
            connection.refresh_token_encrypted = self._encrypt(refreshed_token)
        connection.token_expires_at = now + timedelta(seconds=expires_in)
        connection.status = "connected"
        connection.updated_at = now
        db.commit()
        return tokens["access_token"]

    async def _get_json(
        self,
        base_url: str,
        path: str,
        params: dict[str, str],
        provider: str,
        token: str,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
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

        if not isinstance(payload, dict) or not isinstance(payload.get("items", []), list):
            return {
                "status": "error",
                "items": [],
                "confidence": "unavailable",
                "error": "provider_invalid_response",
            }
        return {"status": "connected", "items": payload.get("items", []), "confidence": "high"}

    def get_calendar(self) -> dict[str, str]:
        now = datetime.now(timezone.utc)
        return {
            "timeMin": now.isoformat(),
            "timeMax": (now + timedelta(days=30)).isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "100",
            "fields": "items(id,summary,start,end,status)",
        }

    def get_tasks(self) -> dict[str, str]:
        return {
            "maxResults": "100",
            "showCompleted": "false",
            "showHidden": "false",
            "fields": "items(id,title,due,status,updated)",
        }

    async def get_coordination(self, db: Session) -> dict[str, Any]:
        """Read the shared Google Calendar and Tasks account for existing platform workflows."""
        try:
            token = await self._get_access_token(db)
        except ValueError as exc:
            error = str(exc) if str(exc).startswith("google_oauth_") else "provider_invalid_response"
            result = {"status": "error", "items": [], "confidence": "unavailable", "error": error}
            return {
                "calendar": result,
                "tasks": result.copy(),
                "conflicts": [],
                "source": "google_calendar_and_tasks",
                "external_actions": "disabled",
            }
        if not token:
            result = {"status": "not_configured", "items": [], "confidence": "unavailable"}
            return {
                "calendar": result,
                "tasks": result.copy(),
                "conflicts": [],
                "source": "google_calendar_and_tasks",
                "external_actions": "disabled",
            }

        calendar_params, task_params = self.get_calendar(), self.get_tasks()
        calendar, tasks = await asyncio.gather(
            self._get_json(
                settings.EA_CALENDAR_BASE_URL,
                settings.EA_CALENDAR_PATH,
                calendar_params,
                "calendar",
                token,
            ),
            self._get_json(
                settings.EA_TASKS_BASE_URL,
                settings.EA_TASKS_PATH,
                task_params,
                "tasks",
                token,
            ),
        )
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

    async def disconnect(self, db: Session) -> dict[str, Any]:
        """Remove the local Google connection and attempt to revoke its refresh token."""
        connection = (
            db.query(GoogleCalendarConnection)
            .filter(GoogleCalendarConnection.shared_slot == 1)
            .with_for_update()
            .first()
        )
        if not connection:
            return {"status": "disconnected", "provider_revoked": True}

        try:
            refresh_token = self._decrypt(connection.refresh_token_encrypted)
        except HTTPException:
            refresh_token = None
        db.delete(connection)
        db.commit()

        if not refresh_token:
            return {"status": "disconnected", "provider_revoked": False}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.REVOKE_URL, data={"token": refresh_token})
            if response.status_code in {200, 400}:
                return {"status": "disconnected", "provider_revoked": True}
        except httpx.HTTPError:
            pass
        return {"status": "disconnected", "provider_revoked": False}


ea_coordination_service = EACoordinationService()
