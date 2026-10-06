# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/student_payments_service.py
from datetime import date, datetime, timezone
import re
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.core.config import settings


class StudentPaymentsService:
    """Read provider payment facts without copying them into local storage."""

    def __init__(self) -> None:
        self._kajabi_access_token: str | None = None
        self._kajabi_token_expires_at = 0.0

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

    async def _kajabi_token(self) -> str:
        now = datetime.now(timezone.utc).timestamp()
        if self._kajabi_access_token and now < self._kajabi_token_expires_at:
            return self._kajabi_access_token
        if not settings.KAJABI_CLIENT_ID or not settings.KAJABI_CLIENT_SECRET:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "kajabi"},
            )

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{settings.KAJABI_API_BASE_URL.rstrip('/')}/v1/oauth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": settings.KAJABI_CLIENT_ID,
                        "client_secret": settings.KAJABI_CLIENT_SECRET,
                    },
                )
                response.raise_for_status()
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                raise HTTPException(status_code=502, detail="Kajabi did not return an access token")
            expires_in = int(payload.get("expires_in") or 3600)
            self._kajabi_access_token = str(token)
            self._kajabi_token_expires_at = now + max(expires_in - 60, 30)
            return self._kajabi_access_token
        except HTTPException:
            raise
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail="Kajabi authentication failed") from exc
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="Kajabi is unavailable or returned an invalid token response") from exc

    async def _kajabi_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        token = await self._kajabi_token()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{settings.KAJABI_API_BASE_URL.rstrip('/')}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.api+json"},
                )
                response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise HTTPException(status_code=503, detail="Kajabi rate limit reached; retry later") from exc
            if exc.response.status_code == 403:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "code": "provider_access_denied",
                        "provider": "kajabi",
                        "message": (
                            "Kajabi denied API access. Verify that the OAuth client is authorized "
                            "for this Kajabi account and the requested resources; a site ID alone "
                            "does not grant API access."
                        ),
                    },
                ) from exc
            raise HTTPException(status_code=502, detail="Kajabi read failed") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Kajabi is unavailable or returned an invalid response") from exc

    async def list_kajabi_offers(self, page: int, per_page: int) -> dict[str, Any]:
        """Read non-archived offers from the configured Kajabi site."""
        if not settings.KAJABI_SITE_ID:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "kajabi"},
            )
        payload = await self._kajabi_get("/v1/offers", {
            "page[number]": page,
            "page[size]": per_page,
            "filter[site_id]": settings.KAJABI_SITE_ID,
            "fields[offers]": "title,currency,status",
        })
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
    ) -> dict[str, Any]:
        """Read Kajabi customers with a currently granted offer; Kajabi owns access status."""
        if not settings.KAJABI_SITE_ID:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "kajabi"},
            )
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": per_page,
            "filter[site_id]": settings.KAJABI_SITE_ID,
            "filter[has_offer_id]": offer_id,
            "fields[customers]": "name,email,external_user_id",
            "sort": "name",
        }
        if search and search.strip():
            params["filter[search]"] = search.strip()
        payload = await self._kajabi_get("/v1/customers", params)
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
    ) -> dict[str, Any]:
        """Read site-scoped financial transaction facts from Kajabi without local copies."""
        if not settings.KAJABI_SITE_ID:
            raise HTTPException(
                status_code=503,
                detail={"code": "provider_not_configured", "provider": "kajabi"},
            )
        params: dict[str, Any] = {
            "page[number]": page,
            "page[size]": per_page,
            "filter[site_id]": settings.KAJABI_SITE_ID,
            "fields[transactions]": "action,state,payment_type,amount_in_cents,currency,created_at,customer",
        }
        if from_date:
            params["filter[start_date]"] = from_date.isoformat()
        if to_date:
            params["filter[end_date]"] = to_date.isoformat()
        payload = await self._kajabi_get("/v1/transactions", params)

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
