# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/writer.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db

router = APIRouter()


@router.get(
    "/metrics",
    dependencies=[Depends(require_permission("agents:trigger"))],
)
async def get_writer_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return writer dashboard summary metrics."""
    try:
        metrics = {
            "totalDocuments": 148,
            "documentsThisMonth": 32,
            "templatesAvailable": 18,
            "agentExecutions": 96,
        }
        return {"metrics": metrics}
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch writer metrics: {str(exc)}",
        )


@router.get(
    "/documents",
    dependencies=[Depends(require_permission("agents:trigger"))],
)
async def get_writer_documents(
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    type: Optional[str] = Query(None, alias="type"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return SOPs, templates, and reports for the writer dashboard."""
    try:
        all_documents = [
            {
                "id": "doc_1",
                "title": "Sales Enrollment SOP",
                "description": "Step-by-step onboarding and qualification flow.",
                "type": "sop",
                "status": "active",
                "version": "2.4",
            },
            {
                "id": "doc_2",
                "title": "Student Success Playbook",
                "description": "Retention and outreach workflow for at-risk students.",
                "type": "sop",
                "status": "active",
                "version": "1.8",
            },
            {
                "id": "doc_3",
                "title": "Marketing Content Template",
                "description": "Reusable social-media caption and campaign brief.",
                "type": "template",
                "status": "draft",
                "version": "4.1",
            },
            {
                "id": "doc_4",
                "title": "Operations Weekly Report",
                "description": "Weekly performance and workflow summary for leadership.",
                "type": "report",
                "status": "active",
                "version": "3.0",
            },
            {
                "id": "doc_5",
                "title": "Client Renewal Script",
                "description": "Call script to support renewals and check-ins.",
                "type": "template",
                "status": "archived",
                "version": "1.2",
            },
        ]

        filtered = all_documents
        if search:
            query = search.lower()
            filtered = [
                doc
                for doc in filtered
                if query in doc["title"].lower() or query in doc["description"].lower()
            ]
        if type and type != "all":
            filtered = [doc for doc in filtered if doc["type"] == type]

        return {"documents": filtered[:limit]}
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch writer documents: {str(exc)}",
        )


@router.get(
    "/agent-templates",
    dependencies=[Depends(require_permission("agents:trigger"))],
)
async def get_writer_agent_templates(
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query("all"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return AI agent templates to support automation workflows."""
    try:
        templates = [
            {
                "id": "template_1",
                "name": "ENY-SALES-SCORE",
                "description": "Lead qualification and scoring automation.",
                "category": "sales",
                "type": "workflow",
                "status": "active",
                "version": "1.9",
                "usageCount": 12,
            },
            {
                "id": "template_2",
                "name": "ENY-MARKETING-RESPONSE",
                "description": "Follow-up campaigns for inbound leads and campaigns.",
                "category": "marketing",
                "type": "workflow",
                "status": "active",
                "version": "2.2",
                "usageCount": 8,
            },
            {
                "id": "template_3",
                "name": "ENY-OPS-HEALTH",
                "description": "Monitoring and alert escalation workflow.",
                "category": "operations",
                "type": "workflow",
                "status": "draft",
                "version": "1.6",
                "usageCount": 5,
            },
            {
                "id": "template_4",
                "name": "ENY-CLIENT-RENEWAL",
                "description": "Retention automation for client outreach and renewals.",
                "category": "sales",
                "type": "workflow",
                "status": "active",
                "version": "2.0",
                "usageCount": 10,
            },
        ]

        if category and category != "all":
            templates = [template for template in templates if template["category"] == category]

        return {"templates": templates[:limit]}
    except Exception as exc:  # pragma: no cover - defensive logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agent templates: {str(exc)}",
        )
