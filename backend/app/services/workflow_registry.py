# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/workflow_registry.py

from __future__ import annotations

from typing import Any



APPROVED_WORKFLOWS: dict[str, dict[str, Any]] = {
    "eny-prog-onboard": {
        "name": "ENY-PROG-ONBOARD",
        "route": "/webhook/eny-prog-onboard",
        "owner": "programs_manager",
        "mode": "shadow",
        "requires_human_approval": True,
        "description": "Prepare onboarding and orientation reminders in draft form before staff review.",
        "phase": "8",
        "status": "approved_for_shadow_mode",
    },
    "eny-prog-monitor": {
        "name": "ENY-PROG-MONITOR",
        "route": "/webhook/eny-prog-monitor",
        "owner": "programs_manager",
        "mode": "shadow",
        "requires_human_approval": True,
        "description": "Generate checked attendance and assignment summaries for human review only.",
        "phase": "8",
        "status": "approved_for_shadow_mode",
    },
    "eny-customer-success-checkin": {
        "name": "ENY-CUSTOMER-SUCCESS-CHECKIN",
        "route": "/webhook/eny-customer-success-checkin",
        "owner": "customer_success",
        "mode": "draft-only",
        "requires_human_approval": True,
        "description": "Draft weekly check-in summaries without sending student-facing messages automatically.",
        "phase": "7",
        "status": "draft_review_only",
    },
    "eny-customer-success-escalation": {
        "name": "ENY-CUSTOMER-SUCCESS-ESCALATION",
        "route": "/webhook/eny-customer-success-escalation",
        "owner": "programs_manager",
        "mode": "manual",
        "requires_human_approval": True,
        "description": "Escalates complaints, payment disputes, and sensitive student issues to a human approver.",
        "phase": "8",
        "status": "requires_human_approval",
    },
}


def get_approved_workflows() -> list[dict[str, Any]]:
    return [
        {
            "name": metadata["name"],
            "route": metadata["route"],
            "owner": metadata["owner"],
            "mode": metadata["mode"],
            "requires_human_approval": metadata["requires_human_approval"],
            "description": metadata["description"],
            "phase": metadata["phase"],
            "status": metadata["status"],
        }
        for _, metadata in APPROVED_WORKFLOWS.items()
    ]


def is_registered_workflow(workflow_name: str) -> bool:
    normalized = (workflow_name or "").strip().lower()
    return normalized in APPROVED_WORKFLOWS
