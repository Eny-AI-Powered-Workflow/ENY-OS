# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/student_lifecycle_service.py

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class StudentLifecycleService:
    """In-memory safety layer for human-reviewed lifecycle actions.

    This module intentionally avoids any automatic outbound actions. It exposes a
    controlled queue and draft-review model so Customer Success can prepare
    follow-up work without bypassing the required human approval gates.
    """

    def __init__(self) -> None:
        self._work_queue: list[dict[str, Any]] = [
            {
                "id": "onboarding-orientation",
                "workflow": "onboarding_orientation",
                "label": "Onboarding / Orientation",
                "student_name": "Pending review",
                "status": "draft",
                "manual_review_required": True,
                "approved_for_send": False,
                "owner": "customer_success",
                "summary": "Orientation reminder and onboarding follow-up are draft-only until staff review.",
                "last_updated": self._utc_now(),
            },
            {
                "id": "at-risk-follow-up",
                "workflow": "at_risk_follow_up",
                "label": "At-risk follow-up",
                "student_name": "Pending review",
                "status": "needs_review",
                "manual_review_required": True,
                "approved_for_send": False,
                "owner": "customer_success",
                "summary": "Risk alerts are based on approved source data only and require staff review before any action.",
                "last_updated": self._utc_now(),
            },
            {
                "id": "assignment-capstone",
                "workflow": "assignment_and_capstone",
                "label": "Assignments / Capstones",
                "student_name": "Pending review",
                "status": "queued",
                "manual_review_required": True,
                "approved_for_send": False,
                "owner": "customer_success",
                "summary": "Assignment reminders are queued as drafts and may be approved only after human review.",
                "last_updated": self._utc_now(),
            },
            {
                "id": "coach-handoff",
                "workflow": "coach_handoff",
                "label": "Coach handoff",
                "student_name": "Pending review",
                "status": "draft",
                "manual_review_required": True,
                "approved_for_send": False,
                "owner": "customer_success",
                "summary": "Coach handoff notes should not trigger a message or external update without approval.",
                "last_updated": self._utc_now(),
            },
            {
                "id": "offboarding-graduation",
                "workflow": "offboarding_graduation",
                "label": "Offboarding / Graduation",
                "student_name": "Pending review",
                "status": "needs_review",
                "manual_review_required": True,
                "approved_for_send": False,
                "owner": "programs_manager",
                "summary": "Graduation and offboarding actions remain human-approved and idempotent.",
                "last_updated": self._utc_now(),
            },
            {
                "id": "alumni-transition",
                "workflow": "alumni_transition",
                "label": "Alumni transition",
                "student_name": "Pending review",
                "status": "queued",
                "manual_review_required": True,
                "approved_for_send": False,
                "owner": "customer_success",
                "summary": "Alumni follow-up is a draft workflow until the accountable team approves the message.",
                "last_updated": self._utc_now(),
            },
        ]
        self._drafts: list[dict[str, Any]] = []
        self._verification_requests: list[dict[str, Any]] = []

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_queue(self) -> dict[str, Any]:
        return {"items": deepcopy(self._work_queue)}

    def create_queue_item(
        self,
        workflow: str,
        student_name: str,
        summary: str,
        status: str = "queued",
        owner: str = "customer_success",
    ) -> dict[str, Any]:
        item = {
            "id": f"{workflow}-{len(self._work_queue) + 1}",
            "workflow": workflow,
            "label": workflow.replace("_", " ").title(),
            "student_name": student_name,
            "status": status,
            "manual_review_required": True,
            "approved_for_send": False,
            "owner": owner,
            "summary": summary,
            "last_updated": self._utc_now(),
        }
        self._work_queue.append(item)
        return deepcopy(item)

    def update_queue_item(self, item_id: str, status: str) -> dict[str, Any]:
        for item in self._work_queue:
            if item["id"] == item_id:
                item["status"] = status
                item["last_updated"] = self._utc_now()
                item["approved_for_send"] = status in {"approved", "approved_for_review"}
                return deepcopy(item)
        raise KeyError(f"Lifecycle item {item_id} was not found")

    def get_drafts(self) -> dict[str, Any]:
        return {"items": deepcopy(self._drafts)}

    def create_communication_draft(
        self,
        student_name: str,
        category: str,
        message: str,
    ) -> dict[str, Any]:
        draft = {
            "id": f"draft-{len(self._drafts) + 1}",
            "student_name": student_name,
            "category": category,
            "message": message,
            "status": "draft",
            "approved_for_send": False,
            "requires_human_approval": True,
            "owner": "customer_success",
            "last_updated": self._utc_now(),
        }
        self._drafts.append(draft)
        return deepcopy(draft)

    def approve_communication_draft(self, draft_id: str, permission_scope: str) -> dict[str, Any]:
        if permission_scope != "students:intervention:approve":
            raise PermissionError("Manager approval is required before a draft can be sent.")

        for draft in self._drafts:
            if draft["id"] == draft_id:
                draft["status"] = "approved_for_review"
                draft["approved_for_send"] = True
                draft["last_updated"] = self._utc_now()
                return deepcopy(draft)
        raise KeyError(f"Draft {draft_id} was not found")

    def get_payment_verification_requests(self) -> dict[str, Any]:
        return {"items": deepcopy(self._verification_requests)}

    def create_payment_verification_request(self, student_name: str, amount: str) -> dict[str, Any]:
        request = {
            "id": f"payment-review-{len(self._verification_requests) + 1}",
            "student_name": student_name,
            "amount": amount,
            "status": "pending_business_support_review",
            "owner": "business_support",
            "requires_human_approval": True,
            "last_updated": self._utc_now(),
        }
        self._verification_requests.append(request)
        return deepcopy(request)

    def update_payment_verification_status(self, request_id: str, status: str, permission_scope: str) -> dict[str, Any]:
        if status == "verified" and permission_scope != "payments:verify":
            raise PermissionError("Only a verifier with payments:verify can mark a payment as verified.")

        for request in self._verification_requests:
            if request["id"] == request_id:
                request["status"] = status
                request["last_updated"] = self._utc_now()
                return deepcopy(request)
        raise KeyError(f"Payment verification request {request_id} was not found")


student_lifecycle_service = StudentLifecycleService()
