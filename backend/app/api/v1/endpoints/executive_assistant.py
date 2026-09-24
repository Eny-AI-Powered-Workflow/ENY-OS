# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/executive_assistant.py

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.agent_log import AgentLog
from app.models.batch_execution_result import BatchExecutionResult
from app.models.operational_alert import OperationalAlert
from app.services.ghl_service import ghl_service

router = APIRouter()

EA_PLAYBOOKS = [
    {"name": "Daily executive briefing", "status": "active", "requires_approval": False},
    {"name": "Meeting preparation", "status": "planned", "requires_approval": True},
    {"name": "Opportunity research", "status": "planned", "requires_approval": True},
    {"name": "Executive follow-up", "status": "planned", "requires_approval": True},
]


def _timestamp(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else str(value) if value else None


@router.get("/briefing", dependencies=[Depends(require_permission("assistant:briefing:read"))])
async def get_executive_briefing(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Return a source-labelled daily briefing for EA and CEO users."""
    generated_at = datetime.now(timezone.utc)
    alerts = db.query(OperationalAlert).filter(
        OperationalAlert.team == "sales_enrollment",
        OperationalAlert.status == "open",
    ).order_by(OperationalAlert.created_at.desc()).limit(10).all()
    active_leads = db.query(BatchExecutionResult).filter(
        BatchExecutionResult.queue_status != "closed",
    ).order_by(BatchExecutionResult.created_at.desc()).limit(100).all()
    unresolved_tasks = db.query(AgentLog).filter(
        AgentLog.status != "success",
    ).order_by(AgentLog.created_at.desc()).limit(20).all()

    try:
        pipeline = await ghl_service.get_pipeline_data()
        crm_status = "connected" if not pipeline.get("error") else "degraded"
    except Exception:
        pipeline = {}
        crm_status = "degraded"

    try:
        sop_row = db.execute(text(
            "select count(*)::int as count from knowledge_documents where department = :department and is_active = true"
        ), {"department": "executive_assistant"}).first()
        sop_chunks = int(sop_row.count if sop_row else 0)
    except Exception:
        sop_chunks = 0

    priorities = [
        {
            "title": alert.message,
            "reason": f"{alert.source} failure requires operational attention",
            "severity": alert.severity,
            "requires_approval": False,
            "source": "operational_alerts",
            "source_timestamp": _timestamp(alert.created_at),
            "confidence": "high",
        }
        for alert in alerts
    ]
    priorities.extend({
        "title": f"Hot lead requires review: {row.contact_name or row.contact_id}",
        "reason": "Active scored lead is not closed",
        "severity": "high",
        "requires_approval": False,
        "source": "batch_execution_results",
        "source_timestamp": _timestamp(row.updated_at or row.created_at),
        "confidence": "high",
    } for row in active_leads if row.category == "hot" and row.queue_status in {"new", "assigned"})

    opportunities = pipeline.get("opportunities", [])[:10]
    return {
        "generated_at": generated_at.isoformat(),
        "role_scope": "executive_assistant",
        "briefing": {
            "priorities": priorities[:20],
            "meetings": {
                "status": "not_connected",
                "items": [],
                "message": "Calendar integration is not connected; no meetings were inferred.",
                "confidence": "unavailable",
            },
            "unresolved_tasks": [
                {
                    "workflow": task.workflow_name,
                    "status": task.status,
                    "created_at": _timestamp(task.created_at),
                    "confidence": "high",
                }
                for task in unresolved_tasks
            ],
            "alerts": [
                {
                    "id": str(alert.id),
                    "severity": alert.severity,
                    "source": alert.source,
                    "message": alert.message,
                    "created_at": _timestamp(alert.created_at),
                }
                for alert in alerts
            ],
            "opportunities": [
                {
                    "id": opportunity.get("id"),
                    "name": opportunity.get("name") or opportunity.get("contactName"),
                    "pipeline": opportunity.get("pipelineName") or opportunity.get("pipelineStageName"),
                    "status": opportunity.get("status"),
                    "value": opportunity.get("monetaryValue") or opportunity.get("expectedValue"),
                    "source_timestamp": opportunity.get("updatedAt") or opportunity.get("createdAt"),
                    "confidence": "high" if opportunity.get("id") else "low",
                    "requires_approval": True,
                }
                for opportunity in opportunities
            ],
        },
        "system_status": {
            "crm": crm_status,
            "open_alerts": len(alerts),
            "sop_chunks": sop_chunks,
            "pipeline_source": "GoHighLevel",
            "generated_at": generated_at.isoformat(),
        },
        "approval_boundary": {
            "message": "Research, outreach, scheduling, and external executive commitments require CEO approval until their dedicated integrations are connected.",
            "automated_actions": [],
            "requires_ceo_approval": True,
        },
        "playbooks": EA_PLAYBOOKS,
    }
