# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/student_success_service.py
import re
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.services.student_payments_service import student_payments_service
from app.services.student_program_sheet_service import student_program_sheet_service


class StudentSuccessService:
    """Join Kajabi's active-offer roster with the approved Program Sheet read model."""

    @staticmethod
    def _normalize_program(value: str | None) -> str:
        return re.sub(r"[^a-z0-9]", "", (value or "").casefold())

    @staticmethod
    def _sheet_configuration_status() -> str:
        if not (
            settings.CUSTOMER_SUCCESS_SHEETS_SERVICE_ACCOUNT_JSON
            and settings.CUSTOMER_SUCCESS_PROGRAM_SHEET_ID
            and settings.CUSTOMER_SUCCESS_PROGRAM_SHEET_RANGE
        ):
            return "not_configured"
        return "connected"

    async def list_offers(self, page: int, per_page: int) -> dict[str, Any]:
        return await student_payments_service.list_kajabi_offers(page, per_page)

    def _match_program_row(
        self,
        rows: list[dict[str, str | None]],
        offer_title: str | None,
    ) -> tuple[dict[str, str | None] | None, str]:
        if not rows:
            return None, "not_found"
        if len(rows) == 1:
            row_program = self._normalize_program(rows[0].get("program"))
            normalized_offer = self._normalize_program(offer_title)
            if row_program and normalized_offer and row_program != normalized_offer:
                return None, "not_found"
            return rows[0], "matched"
        normalized_offer = self._normalize_program(offer_title)
        if normalized_offer:
            exact_matches = [
                row for row in rows
                if self._normalize_program(row.get("program")) == normalized_offer
            ]
            if len(exact_matches) == 1:
                return exact_matches[0], "matched"
        return None, "ambiguous"

    async def _get_active_offer(self, offer_id: str) -> dict[str, Any]:
        offer_result = await student_payments_service.list_kajabi_offers(page=1, per_page=100)
        selected_offer = next((offer for offer in offer_result["offers"] if offer["id"] == offer_id), None)
        if selected_offer is None:
            raise HTTPException(status_code=404, detail="Active Kajabi offer was not found for this site")
        return selected_offer

    async def _sheet_source(self) -> tuple[str, dict[str, list[dict[str, str | None]]]]:
        sheet_status = self._sheet_configuration_status()
        sheet_rows: dict[str, list[dict[str, str | None]]] = {}
        if sheet_status == "connected":
            try:
                sheet_rows = await student_program_sheet_service.records_by_email()
            except HTTPException:
                sheet_status = "unavailable"
        return sheet_status, sheet_rows

    def _enrich_students(
        self,
        customers: list[dict[str, Any]],
        selected_offer: dict[str, Any],
        sheet_status: str,
        sheet_rows: dict[str, list[dict[str, str | None]]],
    ) -> list[dict[str, Any]]:
        offer_id = selected_offer["id"]
        students = []
        for customer in customers:
            email = str(customer.get("email") or "").strip().casefold()
            candidate_rows = sheet_rows.get(email, []) if email else []
            program_row, match_status = self._match_program_row(candidate_rows, selected_offer.get("title"))
            students.append({
                "id": customer["id"],
                "name": customer["name"],
                "email": customer.get("email"),
                "external_user_id": customer.get("external_user_id"),
                "offer_id": offer_id,
                "offer_title": selected_offer["title"],
                "offer_status": customer["offer_status"],
                "program_sheet_status": match_status if sheet_status == "connected" else sheet_status,
                "program": program_row.get("program") if program_row else None,
                "cohort": program_row.get("cohort") if program_row else None,
                "attendance": program_row.get("attendance") if program_row else None,
                "assignment_status": program_row.get("assignment_status") if program_row else None,
                "capstone_status": program_row.get("capstone_status") if program_row else None,
            })
        return students

    async def list_students(
        self,
        offer_id: str,
        page: int,
        per_page: int,
        search: str | None = None,
    ) -> dict[str, Any]:
        offer_id = offer_id.strip()
        if not offer_id:
            raise HTTPException(status_code=422, detail="offer_id is required")
        selected_offer = await self._get_active_offer(offer_id)
        kajabi_result = await student_payments_service.list_kajabi_active_students(
            offer_id=offer_id,
            page=page,
            per_page=per_page,
            search=search,
        )
        sheet_status, sheet_rows = await self._sheet_source()

        return {
            "students": self._enrich_students(kajabi_result["records"], selected_offer, sheet_status, sheet_rows),
            "offer": selected_offer,
            "page": kajabi_result["page"],
            "per_page": kajabi_result["per_page"],
            "total_count": kajabi_result["total_count"],
            "has_more": kajabi_result["has_more"],
            "sources": {"roster": "kajabi_active_offer", "program_sheet": sheet_status},
        }

    async def _all_students_for_offer(self, offer_id: str) -> tuple[list[dict[str, Any]], int | None, str]:
        selected_offer = await self._get_active_offer(offer_id)
        sheet_status, sheet_rows = await self._sheet_source()
        all_students: list[dict[str, Any]] = []
        page = 1
        total_count: int | None = None
        while page <= settings.KAJABI_MAX_STUDENT_PAGES:
            result = await student_payments_service.list_kajabi_active_students(offer_id, page, 100)
            all_students.extend(self._enrich_students(result["records"], selected_offer, sheet_status, sheet_rows))
            total_count = result["total_count"]
            if not result["has_more"]:
                return all_students, total_count, sheet_status
            page += 1
        raise HTTPException(
            status_code=503,
            detail={"code": "source_page_limit_exceeded", "source": "kajabi_active_offer"},
        )

    async def get_metrics(self, offer_id: str) -> dict[str, Any]:
        result = await self.list_students(offer_id, page=1, per_page=1)
        return {
            "metrics": {
                "totalStudents": result["total_count"],
                "activeOffer": result["offer"]["title"],
            },
            "sources": {
                "roster": "kajabi_active_offer",
                "program_sheet": result["sources"]["program_sheet"],
            },
        }

    async def get_progress(self, offer_id: str) -> dict[str, Any]:
        students, total_count, sheet_status = await self._all_students_for_offer(offer_id)
        matched = [student for student in students if student["program_sheet_status"] == "matched"]
        return {
            "progress": {
                "activeStudents": total_count if total_count is not None else len(students),
                "attendanceReported": sum(bool(student["attendance"]) for student in matched) if sheet_status == "connected" else None,
                "assignmentsReported": sum(bool(student["assignment_status"]) for student in matched) if sheet_status == "connected" else None,
                "capstonesReported": sum(bool(student["capstone_status"]) for student in matched) if sheet_status == "connected" else None,
                "programSheetMatches": len(matched) if sheet_status == "connected" else None,
            },
            "sources": {
                "roster": "kajabi_active_offer",
                "program_sheet": sheet_status,
            },
        }


student_success_service = StudentSuccessService()
