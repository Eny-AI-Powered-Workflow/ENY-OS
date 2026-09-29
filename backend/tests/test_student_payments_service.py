# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_student_payments_service.py
import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.student_success import (
    get_student_list,
    get_student_progress,
    get_student_success_metrics,
    router,
)
from app.core.config import settings
from app.services import student_payments_service as payments_module
from app.services.student_payments_service import StudentPaymentsService


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    responses = []
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)


def _required_scopes(route):
    return {
        cell.cell_contents
        for dependency in route.dependant.dependencies
        for cell in (dependency.call.__closure__ or ())
        if isinstance(cell.cell_contents, str)
    }


def test_payment_routes_require_provider_specific_read_scopes():
    routes = {route.path: route for route in router.routes if hasattr(route, "dependant")}

    assert "payments:kajabi:read" in _required_scopes(routes["/payments/kajabi"])
    assert "payments:paystack:read" in _required_scopes(routes["/payments/paystack"])


def test_student_lifecycle_routes_require_read_scope():
    routes = {route.path: route for route in router.routes if hasattr(route, "dependant")}

    for path in ("/metrics", "/students", "/progress"):
        assert "students:read" in _required_scopes(routes[path])


@pytest.mark.asyncio
async def test_student_lifecycle_routes_return_unavailable_instead_of_mock_data():
    handlers = (get_student_success_metrics, get_student_list, get_student_progress)

    for handler in handlers:
        with pytest.raises(HTTPException) as error:
            await handler()
        assert error.value.status_code == 503
        assert error.value.detail == {"code": "source_not_configured", "source": "student_lifecycle"}


def test_normalize_paystack_keeps_only_ngn_and_minimum_fields():
    result = StudentPaymentsService._normalize_paystack_transaction({
        "id": 23,
        "amount": 125000,
        "currency": "NGN",
        "status": "success",
        "reference": "ps-ref-1",
        "paid_at": "2026-09-01T12:00:00Z",
        "customer": {"first_name": "Ada", "last_name": "Okafor", "email": "ada@example.com", "phone": "+2348000000000"},
        "metadata": {"private": "omit"},
    })

    assert result == {
        "transaction_id": "23",
        "provider": "paystack",
        "amount_minor": 125000,
        "currency": "NGN",
        "status": "success",
        "action": None,
        "transaction_date": "2026-09-01T12:00:00Z",
        "reference": "ps-ref-1",
        "customer_name": "Ada Okafor",
        "customer_email": "ada@example.com",
    }
    assert StudentPaymentsService._normalize_paystack_transaction({"currency": "USD"}) is None


def test_normalize_kajabi_joins_minimal_customer_fields():
    records = StudentPaymentsService._normalize_kajabi_response({
        "data": [{
            "id": "txn-1",
            "attributes": {
                "action": "charge",
                "state": "succeeded",
                "amount_in_cents": 4900,
                "currency": "USD",
                "created_at": "2026-09-01T12:00:00Z",
            },
            "relationships": {"customer": {"data": {"id": "customer-1", "type": "customers"}}},
        }],
        "included": [{
            "id": "customer-1",
            "type": "customers",
            "attributes": {"name": "Ada Okafor", "email": "ada@example.com", "phone": "private"},
        }],
    })

    assert records == [{
        "transaction_id": "txn-1",
        "provider": "kajabi",
        "amount_minor": 4900,
        "currency": "USD",
        "status": "succeeded",
        "action": "charge",
        "transaction_date": "2026-09-01T12:00:00Z",
        "reference": "txn-1",
        "customer_name": "Ada Okafor",
        "customer_email": "ada@example.com",
    }]


@pytest.mark.asyncio
async def test_paystack_read_uses_bounded_page_and_filters_currency(monkeypatch):
    FakeAsyncClient.responses = [FakeResponse({
        "status": True,
        "data": [
            {"id": 1, "amount": 125000, "currency": "NGN", "status": "success", "reference": "ngn-1", "customer": {"email": "a@example.com"}},
            {"id": 2, "amount": 1000, "currency": "USD", "status": "success", "reference": "usd-1", "customer": {"email": "b@example.com"}},
        ],
        "meta": {"pagination": {"pageCount": 3}},
    })]
    FakeAsyncClient.calls = []
    monkeypatch.setattr(payments_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "test-secret")

    response = await StudentPaymentsService().list_paystack_transactions(2, 25)

    assert response["provider"] == "paystack"
    assert response["has_more"] is True
    assert len(response["records"]) == 1
    assert response["records"][0]["currency"] == "NGN"
    method, url, kwargs = FakeAsyncClient.calls[0]
    assert method == "GET"
    assert url.endswith("/transaction")
    assert kwargs["params"] == {"page": 2, "perPage": 25}
    assert kwargs["headers"]["Authorization"] == "Bearer test-secret"


@pytest.mark.asyncio
async def test_kajabi_read_authenticates_and_filters_by_site(monkeypatch):
    FakeAsyncClient.responses = [
        FakeResponse({"access_token": "short-lived-token", "expires_in": 3600}),
        FakeResponse({"data": [], "meta": {"total_pages": 1}}),
    ]
    FakeAsyncClient.calls = []
    monkeypatch.setattr(payments_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(settings, "KAJABI_CLIENT_ID", "test-client")
    monkeypatch.setattr(settings, "KAJABI_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "KAJABI_SITE_ID", "site-123")

    response = await StudentPaymentsService().list_kajabi_transactions(1, 25)

    assert response == {"provider": "kajabi", "records": [], "page": 1, "per_page": 25, "has_more": False}
    token_call, transaction_call = FakeAsyncClient.calls
    assert token_call[0] == "POST"
    assert token_call[1].endswith("/v1/oauth/token")
    assert token_call[2]["data"]["grant_type"] == "client_credentials"
    assert transaction_call[0] == "GET"
    params = transaction_call[2]["params"]
    assert params["filter[site_id]"] == "site-123"
    assert params["page[number]"] == 1
    assert params["page[size]"] == 25
    assert params["include"] == "customer"


@pytest.mark.asyncio
async def test_provider_reads_fail_closed_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "")
    with pytest.raises(HTTPException) as error:
        await StudentPaymentsService().list_paystack_transactions(1, 25)

    assert error.value.status_code == 503
    assert error.value.detail["code"] == "provider_not_configured"
