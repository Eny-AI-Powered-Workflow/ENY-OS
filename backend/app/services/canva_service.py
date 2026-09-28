# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/canva_service.py

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.design_system import CanvaConnection, CanvaOAuthState

CANVA_API = "https://api.canva.com/rest/v1"
CANVA_AUTHORIZE = "https://www.canva.com/api/oauth/authorize"
CANVA_TOKEN = f"{CANVA_API}/oauth/token"


class CanvaService:
    def configured(self) -> bool:
        return bool(settings.CANVA_CLIENT_ID and settings.CANVA_CLIENT_SECRET and settings.CANVA_REDIRECT_URI and settings.CANVA_TOKEN_ENCRYPTION_KEY)

    def _fernet(self) -> Fernet:
        if not settings.CANVA_TOKEN_ENCRYPTION_KEY:
            raise HTTPException(status_code=503, detail="Canva token encryption is not configured")
        try:
            return Fernet(settings.CANVA_TOKEN_ENCRYPTION_KEY.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise HTTPException(status_code=503, detail="CANVA_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc

    def _encrypt(self, value: str) -> str:
        return self._fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def _decrypt(self, value: str) -> str:
        try:
            return self._fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeEncodeError) as exc:
            raise HTTPException(status_code=503, detail="Stored Canva credentials could not be decrypted; reconnect Canva") from exc

    def connection_status(self, db: Session, user_id: UUID) -> dict[str, Any]:
        connection = db.query(CanvaConnection).filter(CanvaConnection.user_id == user_id).first()
        return {
            "configured": self.configured(),
            "connected": bool(connection and connection.status == "connected"),
            "status": connection.status if connection else "not_connected",
            "connected_at": connection.connected_at.isoformat() if connection and connection.connected_at else None,
            "token_expires_at": connection.token_expires_at.isoformat() if connection and connection.token_expires_at else None,
            "scopes": connection.scopes if connection else [],
        }

    def authorization_url(self, db: Session, user_id: UUID) -> str:
        if not self.configured():
            raise HTTPException(status_code=503, detail="Configure Canva OAuth client ID, secret, redirect URI, and token encryption key")
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
        state_row = CanvaOAuthState(
            state_hash=hashlib.sha256(state.encode("ascii")).hexdigest(),
            verifier_encrypted=self._encrypt(verifier),
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(state_row)
        db.commit()
        query = urlencode({
            "code_challenge": challenge,
            "code_challenge_method": "s256",
            "scope": settings.CANVA_OAUTH_SCOPES,
            "response_type": "code",
            "client_id": settings.CANVA_CLIENT_ID,
            "state": state,
            "redirect_uri": settings.CANVA_REDIRECT_URI,
        })
        return f"{CANVA_AUTHORIZE}?{query}"

    async def complete_authorization(self, db: Session, code: str, state: str) -> UUID:
        if not self.configured():
            raise HTTPException(status_code=503, detail="Canva OAuth is not configured")
        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        state_row = db.query(CanvaOAuthState).filter(CanvaOAuthState.state_hash == state_hash).with_for_update().first()
        now = datetime.now(timezone.utc)
        if not state_row or state_row.used_at or state_row.expires_at <= now:
            raise HTTPException(status_code=400, detail="Canva authorization state is invalid, expired, or already used")
        verifier = self._decrypt(state_row.verifier_encrypted)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    CANVA_TOKEN,
                    auth=(settings.CANVA_CLIENT_ID, settings.CANVA_CLIENT_SECRET),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={"grant_type": "authorization_code", "code": code, "code_verifier": verifier, "redirect_uri": settings.CANVA_REDIRECT_URI},
                )
                response.raise_for_status()
                tokens = response.json()
        except httpx.HTTPError as exc:
            db.rollback()
            raise HTTPException(status_code=502, detail="Canva authorization exchange failed") from exc
        if not tokens.get("access_token") or not tokens.get("refresh_token"):
            db.rollback()
            raise HTTPException(status_code=502, detail="Canva token response was incomplete")

        expires_at = now + timedelta(seconds=int(tokens.get("expires_in") or 14400))
        connection = db.query(CanvaConnection).filter(CanvaConnection.user_id == state_row.user_id).with_for_update().first()
        values = {
            "access_token_encrypted": self._encrypt(tokens["access_token"]),
            "refresh_token_encrypted": self._encrypt(tokens["refresh_token"]),
            "token_expires_at": expires_at,
            "scopes": str(tokens.get("scope") or settings.CANVA_OAUTH_SCOPES).split(),
            "status": "connected",
            "updated_at": now,
        }
        if connection:
            for key, value in values.items():
                setattr(connection, key, value)
            connection.connected_at = now
        else:
            connection = CanvaConnection(user_id=state_row.user_id, **values)
            db.add(connection)
        state_row.used_at = now
        db.commit()
        return state_row.user_id

    async def access_token(self, db: Session, user_id: UUID) -> str:
        connection = db.query(CanvaConnection).filter(CanvaConnection.user_id == user_id).with_for_update().first()
        if not connection or connection.status != "connected":
            raise HTTPException(status_code=409, detail="Connect Canva to this user before generating a design")
        now = datetime.now(timezone.utc)
        expires_at = connection.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > now + timedelta(seconds=90):
            return self._decrypt(connection.access_token_encrypted)
        if not self.configured():
            raise HTTPException(status_code=503, detail="Canva token refresh configuration is missing")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    CANVA_TOKEN,
                    auth=(settings.CANVA_CLIENT_ID, settings.CANVA_CLIENT_SECRET),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={"grant_type": "refresh_token", "refresh_token": self._decrypt(connection.refresh_token_encrypted)},
                )
                response.raise_for_status()
                tokens = response.json()
        except httpx.HTTPError as exc:
            connection.status = "error"
            db.commit()
            raise HTTPException(status_code=502, detail="Canva token refresh failed; reconnect Canva") from exc
        if not tokens.get("access_token") or not tokens.get("refresh_token"):
            connection.status = "error"
            db.commit()
            raise HTTPException(status_code=502, detail="Canva refresh response was incomplete; reconnect Canva")
        connection.access_token_encrypted = self._encrypt(tokens["access_token"])
        connection.refresh_token_encrypted = self._encrypt(tokens["refresh_token"])
        connection.token_expires_at = now + timedelta(seconds=int(tokens.get("expires_in") or 14400))
        connection.scopes = str(tokens.get("scope") or " ".join(connection.scopes or [])).split()
        connection.status = "connected"
        connection.updated_at = now
        db.commit()
        return tokens["access_token"]

    async def api_request(self, db: Session, user_id: UUID, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self.access_token(db, user_id)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.request(
                    method,
                    f"{CANVA_API}/{path.lstrip('/')}",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=json_body,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            detail = "Canva rejected this operation; verify template access, Autofill availability, and the connected account plan"
            if status_code == 429:
                raise HTTPException(status_code=429, detail="Canva rate limit reached; retry later") from exc
            if status_code in {401, 403}:
                raise HTTPException(status_code=403, detail=detail) from exc
            if status_code == 404:
                raise HTTPException(status_code=404, detail="Canva template or job was not found or is not accessible") from exc
            raise HTTPException(status_code=502, detail=detail) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Canva is currently unavailable") from exc

    async def get_brand_template_dataset(self, db: Session, user_id: UUID, brand_template_id: str) -> dict[str, Any]:
        result = await self.api_request(db, user_id, "GET", f"brand-templates/{brand_template_id}/dataset")
        dataset = result.get("dataset")
        if not isinstance(dataset, dict):
            raise HTTPException(status_code=502, detail="Canva returned an invalid brand-template dataset")
        return dataset

    async def create_autofill(self, db: Session, user_id: UUID, brand_template_id: str, title: str, data: dict[str, Any]) -> dict[str, Any]:
        result = await self.api_request(db, user_id, "POST", "autofills", json_body={
            "type": "create_from_brand_template",
            "brand_template_id": brand_template_id,
            "title": title[:255],
            "data": data,
        })
        job = result.get("job")
        if not isinstance(job, dict) or not job.get("id"):
            raise HTTPException(status_code=502, detail="Canva did not return an Autofill job ID")
        return job

    async def get_autofill_job(self, db: Session, user_id: UUID, job_id: str) -> dict[str, Any]:
        result = await self.api_request(db, user_id, "GET", f"autofills/{job_id}")
        job = result.get("job")
        if not isinstance(job, dict):
            raise HTTPException(status_code=502, detail="Canva returned an invalid Autofill job")
        return job

    async def create_export(self, db: Session, user_id: UUID, design_id: str, export_format: str) -> dict[str, Any]:
        result = await self.api_request(db, user_id, "POST", "exports", json_body={"design_id": design_id, "format": {"type": export_format}})
        job = result.get("job")
        if not isinstance(job, dict) or not job.get("id"):
            raise HTTPException(status_code=502, detail="Canva did not return an export job ID")
        return job

    async def get_export_job(self, db: Session, user_id: UUID, job_id: str) -> dict[str, Any]:
        result = await self.api_request(db, user_id, "GET", f"exports/{job_id}")
        job = result.get("job")
        if not isinstance(job, dict):
            raise HTTPException(status_code=502, detail="Canva returned an invalid export job")
        return job

    async def download_export(self, url: str) -> bytes:
        from urllib.parse import urlparse

        host = (urlparse(url).hostname or "").lower()
        if not url.startswith("https://") or not (host == "canva.com" or host.endswith(".canva.com")):
            raise HTTPException(status_code=502, detail="Canva returned an invalid export URL")
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Unable to download the Canva export") from exc

    async def revoke(self, db: Session, user_id: UUID) -> None:
        connection = db.query(CanvaConnection).filter(CanvaConnection.user_id == user_id).first()
        if not connection:
            return
        connection.status = "revoked"
        connection.access_token_encrypted = "revoked"
        connection.refresh_token_encrypted = "revoked"
        connection.updated_at = datetime.now(timezone.utc)
        db.commit()


canva_service = CanvaService()
