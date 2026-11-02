# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_student_success_work_queue.py

import pytest

from app.services.student_lifecycle_service import StudentLifecycleService


def test_student_lifecycle_queue_is_safe_and_human_review_required():
    service = StudentLifecycleService()

    queue = service.get_queue()

    assert queue["items"]
    assert {item["workflow"] for item in queue["items"]} >= {
        "onboarding_orientation",
        "at_risk_follow_up",
        "assignment_and_capstone",
        "coach_handoff",
        "offboarding_graduation",
        "alumni_transition",
    }
    assert all(item["manual_review_required"] is True for item in queue["items"])
    assert all(item["status"] in {"draft", "queued", "needs_review"} for item in queue["items"])


def test_communication_drafts_are_draft_only_until_manager_approval():
    service = StudentLifecycleService()

    draft = service.create_communication_draft(
        student_name="Ada Example",
        category="check_in",
        message="Please reply to your check-in summary.",
    )

    assert draft["status"] == "draft"
    assert draft["approved_for_send"] is False

    with pytest.raises(PermissionError):
        service.approve_communication_draft(draft["id"], "students:attendance:write")

    approved = service.approve_communication_draft(draft["id"], "students:intervention:approve")
    assert approved["status"] == "approved_for_review"
    assert approved["approved_for_send"] is True


def test_payment_verification_requests_stay_outside_customer_success_write_privileges():
    service = StudentLifecycleService()

    request = service.create_payment_verification_request(
        student_name="Ada Example",
        amount="NGN 45,000",
    )

    assert request["owner"] == "business_support"
    assert request["requires_human_approval"] is True
    assert request["status"] == "pending_business_support_review"

    with pytest.raises(PermissionError):
        service.update_payment_verification_status(request["id"], "verified", "students:attendance:write")

    verified = service.update_payment_verification_status(request["id"], "verified", "payments:verify")
    assert verified["status"] == "verified"
