# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_student_success_sources.py
import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-placeholder")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-placeholder")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-placeholder")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services import student_success_service as service_module
from app.services import student_program_sheet_service as sheet_module
from app.services.student_payments_service import StudentPaymentsService
from app.services.student_program_sheet_service import StudentProgramSheetService
from app.services.student_success_service import StudentSuccessService


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeGoogleClient:
    responses = []
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)


def test_program_sheet_parser_maps_header_aliases_and_normalizes_email():
    records = StudentProgramSheetService._parse_values([
        ["Student Email", "Program Name", "Cohort", "Attendance Status", "Assignment Completion", "Capstone Progress", "Private Notes"],
        ["  ADA@EXAMPLE.COM ", "Business Analysis", "2026-Q3", "8/10 sessions", "Submitted", "In progress", "not returned"],
    ], max_rows=10)

    assert records == {
        "ada@example.com": [{
            "program": "Business Analysis",
            "cohort": "2026-Q3",
            "attendance": "8/10 sessions",
            "assignment_status": "Submitted",
            "capstone_status": "In progress",
        }]
    }


def test_program_sheet_parser_rejects_missing_or_ambiguous_email_headers():
    with pytest.raises(HTTPException) as missing:
        StudentProgramSheetService._parse_values([["Name", "Cohort"]], max_rows=10)
    assert missing.value.status_code == 503
    assert missing.value.detail["code"] == "source_schema_invalid"

    with pytest.raises(HTTPException) as duplicate:
        StudentProgramSheetService._parse_values([["Email", "Student Email"]], max_rows=10)
    assert duplicate.value.status_code == 503
    assert duplicate.value.detail["code"] == "source_schema_ambiguous"


def test_program_sheet_parser_enforces_configured_row_limit():
    with pytest.raises(HTTPException) as error:
        StudentProgramSheetService._parse_values([["Email"], ["one@example.com"], ["two@example.com"]], max_rows=1)

    assert error.value.status_code == 503
    assert error.value.detail["code"] == "source_limit_exceeded"


def test_program_sheet_row_for_another_program_is_not_joined():
    service = StudentSuccessService()

    row, status = service._match_program_row(
        [{"program": "Data Analytics", "attendance": "10/10"}],
        "Business Analysis",
    )

    assert row is None
    assert status == "not_found"


@pytest.mark.asyncio
async def test_program_sheet_reads_with_google_readonly_scope_and_minimum_fields(monkeypatch):
    FakeGoogleClient.responses = [
        FakeResponse({"access_token": "google-read-token", "expires_in": 3600}),
        FakeResponse({"values": [
            ["Email", "Program", "Cohort", "Attendance", "Assignment Status", "Capstone", "Private Notes"],
            ["ada@example.com", "Business Analysis", "Q3", "8/10", "Submitted", "In progress", "private"],
        ]}),
    ]
    FakeGoogleClient.calls = []
    monkeypatch.setattr(sheet_module.httpx, "AsyncClient", FakeGoogleClient)
    signed_claims = {}

    def encode_assertion(claims, private_key, algorithm):
        signed_claims.update(claims)
        assert private_key == "test-private-key"
        assert algorithm == "RS256"
        return "signed-assertion"

    monkeypatch.setattr(sheet_module.jwt, "encode", encode_assertion)
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_SHEETS_SERVICE_ACCOUNT_JSON", '{"client_email":"reader@example.iam.gserviceaccount.com","private_key":"test-private-key"}')
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_ID", "sheet-123")
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_RANGE", "'Students Program'!A1:Z5001")
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_MAX_ROWS", 5000)

    records = await StudentProgramSheetService().records_by_email()

    assert signed_claims["scope"] == "https://www.googleapis.com/auth/spreadsheets.readonly"
    assert records["ada@example.com"][0]["attendance"] == "8/10"
    assert "private" not in repr(records)
    sheet_call = FakeGoogleClient.calls[1]
    assert sheet_call[0] == "GET"
    assert "sheet-123" in sheet_call[1]
    assert sheet_call[2]["headers"]["Authorization"] == "Bearer google-read-token"


@pytest.mark.asyncio
async def test_kajabi_offer_and_active_customer_requests_are_site_and_scope_filtered(monkeypatch):
    provider = StudentPaymentsService()
    monkeypatch.setattr(settings, "KAJABI_SITE_ID", "site-1")
    get = AsyncMock(side_effect=[
        {"data": [
            {"id": "offer-active", "attributes": {"title": "Active", "currency": "USD", "status": "active"}},
            {"id": "offer-archived", "attributes": {"title": "Archived", "currency": "USD", "status": "archived"}},
        ], "meta": {"total_pages": 1, "total_count": 2}},
        {"data": [{"id": "customer-1", "attributes": {"name": "Ada Student", "email": "ada@example.com", "external_user_id": "ext-1"}}], "meta": {"total_pages": 3, "total_count": 26}},
    ])
    monkeypatch.setattr(provider, "_kajabi_get", get)

    offers = await provider.list_kajabi_offers(1, 100)
    students = await provider.list_kajabi_active_students("offer-active", 2, 25, "ada")

    assert offers["offers"] == [{"id": "offer-active", "title": "Active", "currency": "USD"}]
    assert students["records"] == [{
        "id": "customer-1",
        "name": "Ada Student",
        "email": "ada@example.com",
        "external_user_id": "ext-1",
        "offer_id": "offer-active",
        "offer_status": "granted",
    }]
    assert students["total_count"] == 26
    assert students["has_more"] is True
    customer_params = get.await_args_list[1].args[1]
    assert customer_params["filter[site_id]"] == "site-1"
    assert customer_params["filter[has_offer_id]"] == "offer-active"
    assert customer_params["filter[search]"] == "ada"
    assert customer_params["fields[customers]"] == "name,email,external_user_id"


@pytest.mark.asyncio
async def test_student_join_uses_kajabi_id_and_matches_program_row_by_email_and_offer(monkeypatch):
    service = StudentSuccessService()
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_SHEETS_SERVICE_ACCOUNT_JSON", "configured")
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_ID", "sheet-id")
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_RANGE", "Program!A1:Z5001")
    monkeypatch.setattr(
        service_module.student_payments_service,
        "list_kajabi_offers",
        AsyncMock(return_value={"offers": [{"id": "offer-1", "title": "Business Analysis"}]}),
    )
    monkeypatch.setattr(
        service_module.student_payments_service,
        "list_kajabi_active_students",
        AsyncMock(return_value={
            "records": [{"id": "kajabi-123", "name": "Ada Student", "email": "ADA@example.com", "external_user_id": "ext-123", "offer_id": "offer-1", "offer_status": "granted"}],
            "page": 1,
            "per_page": 25,
            "total_count": 1,
            "total_pages": 1,
            "has_more": False,
        }),
    )
    sheet_read = AsyncMock(return_value={"ada@example.com": [
        {"program": "Data Analytics", "cohort": "Q2", "attendance": "2/10", "assignment_status": "Missing", "capstone_status": None},
        {"program": "Business Analysis", "cohort": "Q3", "attendance": "8/10", "assignment_status": "Submitted", "capstone_status": "In progress"},
    ]})
    monkeypatch.setattr(service_module.student_program_sheet_service, "records_by_email", sheet_read)

    result = await service.list_students("offer-1", 1, 25)

    assert result["students"] == [{
        "id": "kajabi-123",
        "name": "Ada Student",
        "email": "ADA@example.com",
        "external_user_id": "ext-123",
        "offer_id": "offer-1",
        "offer_title": "Business Analysis",
        "offer_status": "granted",
        "program_sheet_status": "matched",
        "program": "Business Analysis",
        "cohort": "Q3",
        "attendance": "8/10",
        "assignment_status": "Submitted",
        "capstone_status": "In progress",
    }]
    assert sheet_read.await_count == 1


@pytest.mark.asyncio
async def test_student_roster_stays_available_when_program_sheet_is_not_configured(monkeypatch):
    service = StudentSuccessService()
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_SHEETS_SERVICE_ACCOUNT_JSON", "")
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_ID", "")
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_RANGE", "")
    monkeypatch.setattr(
        service_module.student_payments_service,
        "list_kajabi_offers",
        AsyncMock(return_value={"offers": [{"id": "offer-1", "title": "Business Analysis"}]}),
    )
    monkeypatch.setattr(
        service_module.student_payments_service,
        "list_kajabi_active_students",
        AsyncMock(return_value={
            "records": [{"id": "kajabi-123", "name": "Ada Student", "email": "ada@example.com", "external_user_id": None, "offer_id": "offer-1", "offer_status": "granted"}],
            "page": 1,
            "per_page": 25,
            "total_count": 1,
            "total_pages": 1,
            "has_more": False,
        }),
    )

    result = await service.list_students("offer-1", 1, 25)

    assert result["students"][0]["program_sheet_status"] == "not_configured"
    assert result["students"][0]["attendance"] is None
    assert result["sources"]["roster"] == "kajabi_active_offer"
    assert result["sources"]["program_sheet"] == "not_configured"


@pytest.mark.asyncio
async def test_progress_coverage_aggregates_only_active_offer_students(monkeypatch):
    service = StudentSuccessService()
    monkeypatch.setattr(settings, "KAJABI_MAX_STUDENT_PAGES", 3)
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_SHEETS_SERVICE_ACCOUNT_JSON", "configured")
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_ID", "sheet-id")
    monkeypatch.setattr(settings, "CUSTOMER_SUCCESS_PROGRAM_SHEET_RANGE", "Program!A1:Z5001")
    monkeypatch.setattr(
        service_module.student_payments_service,
        "list_kajabi_offers",
        AsyncMock(return_value={"offers": [{"id": "offer-1", "title": "Business Analysis"}]}),
    )
    monkeypatch.setattr(
        service_module.student_payments_service,
        "list_kajabi_active_students",
        AsyncMock(return_value={
            "records": [
                {"id": "kajabi-1", "name": "Ada", "email": "ada@example.com", "offer_status": "granted"},
                {"id": "kajabi-2", "name": "Sam", "email": "sam@example.com", "offer_status": "granted"},
            ],
            "page": 1,
            "per_page": 100,
            "total_count": 2,
            "total_pages": 1,
            "has_more": False,
        }),
    )
    sheet_read = AsyncMock(return_value={
        "ada@example.com": [{"program": "Business Analysis", "attendance": "8/10", "assignment_status": "Submitted", "capstone_status": None}],
    })
    monkeypatch.setattr(service_module.student_program_sheet_service, "records_by_email", sheet_read)

    result = await service.get_progress("offer-1")

    assert result["progress"] == {
        "activeStudents": 2,
        "attendanceReported": 1,
        "assignmentsReported": 1,
        "capstonesReported": 0,
        "programSheetMatches": 1,
    }
    assert result["sources"] == {"roster": "kajabi_active_offer", "program_sheet": "connected"}
    assert sheet_read.await_count == 1
