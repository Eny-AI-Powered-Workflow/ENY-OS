# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/student_payments_service.py
from datetime import date, datetime, timezone
import hashlib
import re
from typing import Any
from urllib.parse import quote

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.kajabi_connection import KajabiConnection


class StudentPaymentsService:
    """Read provider payment facts without copying them into local storage."""

    def __init__(self) -> None:
        self._kajabi_access_token: str | None = None
        self._kajabi_token_expires_at = 0.0
        self._kajabi_token_key: str | None = None

    def _kajabi_fernet(self) -> Fernet:
        if not settings.KAJABI_CREDENTIAL_ENCRYPTION_KEY:
            raise HTTPException(
                status_code=503,
                detail="Kajabi credential encryption is not configured on the backend.",
            )
        try:
            return Fernet(settings.KAJABI_CREDENTIAL_ENCRYPTION_KEY.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="KAJABI_CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key.",
            ) from exc

    def _encrypt_kajabi_credential(self, value: str) -> str:
        return self._kajabi_fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def _decrypt_kajabi_credential(self, value: str) -> str:
        try:
            return self._kajabi_fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Stored Kajabi credentials could not be decrypted. Reconnect Kajabi.",
            ) from exc

    def _kajabi_configuration(self, db: Session | None = None) -> tuple[str, str, str, str, datetime | None]:
        connection = None
        if db is not None:
            connection = (
                db.query(KajabiConnection)
                .filter(KajabiConnection.shared_slot == 1)
                .first()
            )
        if connection is not None:
            return (
                self._decrypt_kajabi_credential(connection.client_id_encrypted),
                self._decrypt_kajabi_credential(connection.client_secret_encrypted),
                self._decrypt_kajabi_credential(connection.site_id_encrypted),
                "database",
                connection.last_validated_at,
            )
        return (
            settings.KAJABI_CLIENT_ID,
            settings.KAJABI_CLIENT_SECRET,
            settings.KAJABI_SITE_ID,
            "environment",
            None,
        )

    def kajabi_connection_status(self, db: Session) -> dict[str, Any]:
        """Return shared Kajabi connection metadata without exposing credentials."""
        client_id, client_secret, site_id, source, validated_at = self._kajabi_configuration(db)
        connected = bool(client_id and client_secret and site_id)
        return {
            "configured": connected,
            "connected": connected,
            "source": source if connected else "not_configured",
            "site_id": site_id if connected else None,
            "last_validated_at": validated_at.isoformat() if validated_at else None,
            "can_disconnect": source == "database" and connected,
        }

    async def connect_kajabi(
        self,
        db: Session,
        client_id: str,
        client_secret: str,
        site_id: str,
    ) -> dict[str, Any]:
        """Validate Kajabi credentials and site access before saving encrypted credentials."""
        client_id = client_id.strip()
        client_secret = client_secret.strip()
        site_id = site_id.strip()
        if not client_id or not client_secret or not site_id:
            raise HTTPException(status_code=422, detail="Client ID, client secret, and Site ID are required.")

        # Fail before contacting Kajabi if credentials cannot be safely persisted.
        self._kajabi_fernet()
        token, _ = await self._exchange_kajabi_token(client_id, client_secret)
        payload = await self._kajabi_get(
            "/v1/offers",
            {
                "page[number]": 1,
                "page[size]": 1,
                "filter[site_id]": site_id,
                "fields[offers]": "title,currency,status",
            },
            token=token,
        )
        if not isinstance(payload.get("data"), list):
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_response_invalid",
                    "provider": "kajabi",
                    "message": "Kajabi did not return valid offer data for the configured Site ID.",
                },
            )

        connection = (
            db.query(KajabiConnection)
            .filter(KajabiConnection.shared_slot == 1)
            .first()
        )
        credentials = {
            "client_id_encrypted": self._encrypt_kajabi_credential(client_id),
            "client_secret_encrypted": self._encrypt_kajabi_credential(client_secret),
            "site_id_encrypted": self._encrypt_kajabi_credential(site_id),
            "last_validated_at": datetime.now(timezone.utc),
        }
        if connection is None:
            connection = KajabiConnection(shared_slot=1, **credentials)
            db.add(connection)
        else:
            for key, value in credentials.items():
                setattr(connection, key, value)
        db.commit()
        self._clear_kajabi_token_cache()
        return self.kajabi_connection_status(db)

    def disconnect_kajabi(self, db: Session) -> dict[str, Any]:
        """Remove the shared database-managed Kajabi credentials."""
        connection = (
            db.query(KajabiConnection)
            .filter(KajabiConnection.shared_slot == 1)
            .first()
        )
        if connection is not None:
            db.delete(connection)
            db.commit()
        self._clear_kajabi_token_cache()
        return self.kajabi_connection_status(db)

    def _clear_kajabi_token_cache(self) -> None:
        self._kajabi_access_token = None
        self._kajabi_token_expires_at = 0.0
        self._kajabi_token_key = None

    @staticmethod
    def _amount_minor(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def _normalize_paystack_transaction(cls, transaction: dict[str, Any]) -> dict[str, Any] | None:
        currency = str(transaction.get("currency") or "").upper()
        if currency != "NGN":
            return None

        customer = transaction.get("customer") or {}
        name = " ".join(
            part for part in (
                cls._text(customer.get("first_name")),
                cls._text(customer.get("last_name")),
            ) if part
        ) or cls._text(customer.get("name"))
        return {
            "transaction_id": cls._text(transaction.get("id")),
            "provider": "paystack",
            "customer_id": cls._text(customer.get("id")),
            "amount_minor": cls._amount_minor(transaction.get("amount")),
            "currency": currency,
            "status": cls._text(transaction.get("status")) or "unknown",
            "action": None,
            "transaction_date": cls._text(transaction.get("paid_at") or transaction.get("created_at")),
            "reference": cls._text(transaction.get("reference")),
            "customer_name": name,
            "customer_email": cls._text(customer.get("email")),
        }

    @classmethod
    def _normalize_kajabi_response(cls, payload: dict[str, Any]) -> list[dict[str, Any]]:
        customers = {
            str(item.get("id")): item.get("attributes") or {}
            for item in payload.get("included", [])
            if item.get("type") == "customers"
        }
        normalized: list[dict[str, Any]] = []
        for transaction in payload.get("data", []):
            attributes = transaction.get("attributes") or {}
            customer_data = ((transaction.get("relationships") or {}).get("customer") or {}).get("data") or {}
            customer = customers.get(str(customer_data.get("id")), {})
            normalized.append({
                "transaction_id": cls._text(transaction.get("id")),
                "provider": "kajabi",
                "customer_id": cls._text(customer_data.get("id")),
                "amount_minor": cls._amount_minor(attributes.get("amount_in_cents")),
                "currency": str(attributes.get("currency") or "USD").upper(),
                "status": cls._text(attributes.get("state")) or "unknown",
                "action": cls._text(attributes.get("action")),
                "transaction_date": cls._text(attributes.get("created_at")),
                "reference": cls._text(transaction.get("id")),
                "customer_name": cls._text(customer.get("name")),
                "customer_email": cls._text(customer.get("email")),
            })
        return normalized

    async def list_paystack_transactions(
        self,
        page: int,
        per_page: int,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        """Read transaction facts from Paystack; keep the payment processor authoritative."""
        if not settings.PAYSTACK_SECRET_KEY:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "paystack"},
            )

        params: dict[str, Any] = {"page": page, "perPage": per_page}
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/transaction",
                    params=params,
                    headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
                )
                response.raise_for_status()
            payload = response.json()
            if payload.get("status") is not True:
                raise HTTPException(status_code=502, detail="Paystack did not return transaction data")
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise HTTPException(status_code=503, detail="Paystack rate limit reached; retry later") from exc
            raise HTTPException(status_code=502, detail="Paystack transaction read failed") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Paystack is unavailable or returned an invalid response") from exc

        source_records = payload.get("data") or []
        records = [
            record for record in (self._normalize_paystack_transaction(item) for item in source_records)
            if record is not None
        ]
        pagination = payload.get("meta", {}).get("pagination", {})
        page_count = pagination.get("pageCount")
        return {
            "provider": "paystack",
            "records": records,
            "page": page,
            "per_page": per_page,
            "has_more": page < page_count if isinstance(page_count, int) else len(source_records) >= per_page,
        }

    async def verify_paystack_transaction(self, reference: str) -> dict[str, Any]:
        """Recheck one Paystack transaction; Paystack remains the payment source of truth."""
        if not re.fullmatch(r"[A-Za-z0-9.=-]{1,100}", reference):
            raise HTTPException(status_code=422, detail="Invalid Paystack transaction reference")
        if not settings.PAYSTACK_SECRET_KEY:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "paystack"},
            )

        encoded_reference = quote(reference, safe="")
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{settings.PAYSTACK_BASE_URL.rstrip('/')}/transaction/verify/{encoded_reference}",
                    headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
                )
                response.raise_for_status()
            payload = response.json()
            if payload.get("status") is not True:
                raise HTTPException(status_code=404, detail="Paystack did not find this transaction reference")
            transaction = payload.get("data")
            if not isinstance(transaction, dict) or str(transaction.get("reference") or "") != reference:
                raise HTTPException(status_code=502, detail="Paystack returned a mismatched transaction reference")
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise HTTPException(status_code=503, detail="Paystack rate limit reached; retry later") from exc
            if exc.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Paystack transaction reference was not found") from exc
            raise HTTPException(status_code=502, detail="Paystack transaction verification failed") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Paystack is unavailable or returned an invalid response") from exc

        currency = str(transaction.get("currency") or "").upper()
        provider_status = self._text(transaction.get("status")) or "unknown"
        return {
            "provider": "paystack",
            "reference": reference,
            "provider_status": provider_status,
            "currency": currency,
            "amount_minor": self._amount_minor(transaction.get("amount")),
            "transaction_date": self._text(transaction.get("paid_at") or transaction.get("created_at")),
            "verification_status": "verified" if provider_status.lower() == "success" and currency == "NGN" else "not_confirmed",
        }

    async def _exchange_kajabi_token(self, client_id: str, client_secret: str) -> tuple[str, int]:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{settings.KAJABI_API_BASE_URL.rstrip('/')}/v1/oauth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                )
                response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Kajabi OAuth response must be an object")
            token = payload.get("access_token")
            if not token:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "code": "provider_response_invalid",
                        "provider": "kajabi",
                        "message": "Kajabi did not return an access token. Verify the Public API client configuration.",
                    },
                )
            return str(token), int(payload.get("expires_in") or 3600)
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 429:
                raise HTTPException(status_code=503, detail="Kajabi rate limit reached; retry later") from exc
            if status_code >= 500:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "code": "provider_unavailable",
                        "provider": "kajabi",
                        "message": f"Kajabi's OAuth service is unavailable (HTTP {status_code}). Retry later.",
                    },
                ) from exc
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_auth_failed",
                    "provider": "kajabi",
                    "message": (
                        f"Kajabi rejected the OAuth client credentials (HTTP {status_code}). "
                        "Verify the client ID and secret from Kajabi Public API settings."
                    ),
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_unavailable",
                    "provider": "kajabi",
                    "message": "Could not reach Kajabi's OAuth service. Check connectivity and retry.",
                },
            ) from exc
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_response_invalid",
                    "provider": "kajabi",
                    "message": "Kajabi returned an invalid OAuth token response.",
                },
            ) from exc

    async def _kajabi_token(self, db: Session | None = None) -> str:
        client_id, client_secret, _, _, _ = self._kajabi_configuration(db)
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "kajabi"},
            )

        token_key = hashlib.sha256(
            f"{settings.KAJABI_API_BASE_URL}\0{client_id}\0{client_secret}".encode("utf-8")
        ).hexdigest()
        now = datetime.now(timezone.utc).timestamp()
        if (
            self._kajabi_access_token
            and self._kajabi_token_key == token_key
            and now < self._kajabi_token_expires_at
        ):
            return self._kajabi_access_token
        token, expires_in = await self._exchange_kajabi_token(client_id, client_secret)
        self._kajabi_access_token = token
        self._kajabi_token_key = token_key
        self._kajabi_token_expires_at = now + max(expires_in - 60, 30)
        return self._kajabi_access_token

    async def _kajabi_get(
        self,
        path: str,
        params: dict[str, Any],
        db: Session | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        token = token or await self._kajabi_token(db)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{settings.KAJABI_API_BASE_URL.rstrip('/')}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.api+json"},
                )
                response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Kajabi API response must be an object")
            return payload
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 429:
                raise HTTPException(status_code=503, detail="Kajabi rate limit reached; retry later") from exc
            if status_code in (401, 403):
                message = (
                    "Kajabi rejected the access token (HTTP 401). Check the backend OAuth credentials."
                    if status_code == 401
                    else (
                        "Kajabi denied API access (HTTP 403). Verify that this OAuth client is authorized "
                        "for the account and requested resources; a Site ID alone does not grant access."
                    )
                )
                raise HTTPException(
                    status_code=502,
                    detail={
                        "code": "provider_access_denied",
                        "provider": "kajabi",
                        "message": message,
                    },
                ) from exc
            if status_code == 404:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "code": "provider_resource_not_found",
                        "provider": "kajabi",
                        "message": (
                            "Kajabi could not find the requested API resource (HTTP 404). "
                            "Check the API base URL, endpoint availability, and configured Site ID."
                        ),
                    },
                ) from exc
            if status_code in (400, 422):
                raise HTTPException(
                    status_code=502,
                    detail={
                        "code": "provider_request_rejected",
                        "provider": "kajabi",
                        "message": (
                            f"Kajabi rejected the request (HTTP {status_code}). "
                            "Check the Site ID and the API resource/filter configuration."
                        ),
                    },
                ) from exc
            if status_code >= 500:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "code": "provider_unavailable",
                        "provider": "kajabi",
                        "message": f"Kajabi's API is unavailable (HTTP {status_code}). Retry later.",
                    },
                ) from exc
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_request_failed",
                    "provider": "kajabi",
                    "message": f"Kajabi's API request failed (HTTP {status_code}).",
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_unavailable",
                    "provider": "kajabi",
                    "message": "Could not reach Kajabi's API. Check connectivity and retry.",
                },
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "provider_response_invalid",
                    "provider": "kajabi",
                    "message": "Kajabi returned an invalid API response.",
                },
            ) from exc

    async def list_kajabi_offers(
        self,
        page: int,
        per_page: int,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Read non-archived offers from the configured Kajabi site."""
        site_id = self._kajabi_configuration(db)[2]
        if not site_id:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "kajabi"},
            )
        payload = await self._kajabi_get("/v1/offers", {
            "page[number]": page,
            "page[size]": per_page,
            "filter[site_id]": site_id,
            "fields[offers]": "title,currency,status",
        }, db=db)
        records = []
        for offer in payload.get("data", []):
            attributes = offer.get("attributes") or {}
            if str(attributes.get("status") or "active").lower() != "active":
                continue
            records.append({
                "id": str(offer.get("id")),
                "title": self._text(attributes.get("title")) or "Untitled offer",
                "currency": str(attributes.get("currency") or "USD").upper(),
            })
        meta = payload.get("meta") or {}
        total_pages = meta.get("total_pages")
        return {
            "provider": "kajabi",
            "offers": records,
            "page": page,
            "per_page": per_page,
            "has_more": page < total_pages if isinstance(total_pages, int) else len(records) >= per_page,
        }

    async def list_kajabi_active_students(
        self,
        offer_id: str,
        page: int,
        per_page: int,
        search: str | None = None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Read Kajabi customers with a currently granted offer; Kajabi owns access status."""
        site_id = self._kajabi_configuration(db)[2]
        if not site_id:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "kajabi"},
            )
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": per_page,
            "filter[site_id]": site_id,
            "filter[has_offer_id]": offer_id,
            "fields[customers]": "name,email,external_user_id",
            "sort": "name",
        }
        if search and search.strip():
            params["filter[search]"] = search.strip()
        payload = await self._kajabi_get("/v1/customers", params, db=db)
        records = []
        for customer in payload.get("data", []):
            attributes = customer.get("attributes") or {}
            records.append({
                "id": str(customer.get("id")),
                "name": self._text(attributes.get("name")) or "Name unavailable",
                "email": self._text(attributes.get("email")),
                "external_user_id": self._text(attributes.get("external_user_id")),
                "offer_id": offer_id,
                "offer_status": "granted",
            })
        meta = payload.get("meta") or {}
        total_pages = meta.get("total_pages")
        return {
            "provider": "kajabi",
            "records": records,
            "page": page,
            "per_page": per_page,
            "total_count": meta.get("total_count"),
            "total_pages": total_pages,
            "has_more": page < total_pages if isinstance(total_pages, int) else len(records) >= per_page,
        }

    async def list_kajabi_transactions(
        self,
        page: int,
        per_page: int,
        from_date: date | None = None,
        to_date: date | None = None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Read site-scoped financial transaction facts from Kajabi without local copies."""
        site_id = self._kajabi_configuration(db)[2]
        if not site_id:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "kajabi"},
            )
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": per_page,
            "filter[site_id]": site_id,
            "fields[transactions]": "action,state,payment_type,amount_in_cents,currency,created_at,customer",
        }
        if from_date:
            params["filter[start_date]"] = from_date.isoformat()
        if to_date:
            params["filter[end_date]"] = to_date.isoformat()
        payload = await self._kajabi_get("/v1/transactions", params, db=db)

        records = self._normalize_kajabi_response(payload)
        meta = payload.get("meta") or {}
        total_pages = meta.get("total_pages")
        return {
            "provider": "kajabi",
            "records": records,
            "page": page,
            "per_page": per_page,
            "has_more": page < total_pages if isinstance(total_pages, int) else len(records) >= per_page,
        }


student_payments_service = StudentPaymentsService()
