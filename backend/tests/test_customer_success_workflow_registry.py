# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_customer_success_workflow_registry.py

from app.services.n8n_service import N8NService


def test_customer_success_registry_only_allows_approved_workflows():
    service = N8NService()
    service.mock_mode = True

    approved = [
        "eny-prog-onboard",
        "eny-prog-monitor",
        "eny-customer-success-checkin",
        "eny-customer-success-escalation",
    ]

    for workflow_name in approved:
        result = service.trigger_workflow_sync(workflow_name, {"approved": True})
        assert result["status"] in {"success", "mocked"}

    blocked = service.trigger_workflow_sync("eny-bad-workflow", {"approved": False})
    assert blocked["status"] == "error"
    assert "not registered" in blocked["error"].lower()
