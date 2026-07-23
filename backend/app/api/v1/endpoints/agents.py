# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/agents.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Dict, Any
from app.api.deps import require_permission
from app.services.n8n_service import N8NService
from app.services.ghl_service import GHLService
from app.models.audit_log import AuditLog
from app.db.session import get_db
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
n8n_service = N8NService()
ghl_service = GHLService()


@router.post("/trigger/{workflow_name}", dependencies=[Depends(require_permission("agents:trigger"))])
async def trigger_agent_workflow(
    workflow_name: str,
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger an n8n workflow (agent) by name.
    Requires agents:trigger permission.

    This endpoint is the gateway to n8n workflows.
    Permission is checked here, then the workflow is triggered.
    n8n handles the actual automation logic.
    """
    try:
        # Log the trigger attempt (audit log is handled by require_permission dependency)
        # But we can add additional logging here if needed
        logger.info(f"Triggering workflow '{workflow_name}' with data: {data}")

        # Trigger the workflow in n8n
        result = await n8n_service.trigger_workflow(
            workflow_name=workflow_name,
            data=data
        )

        # Add background task to log the agent execution if needed
        # background_tasks.add_task(log_agent_execution, workflow_name, data, result, db)

        return {
            "status": "success",
            "workflow": workflow_name,
            "result": result
        }

    except Exception as e:
        logger.error(f"Failed to trigger workflow {workflow_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger workflow: {str(e)}"
        )


async def log_agent_execution(
    workflow_name: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    db: Session
):
    """
    Background task to log agent execution details.
    This could be expanded to store in agent_logs table.
    """
    try:
        # This would go into an agent_logs table (to be created)
        # For now, we'll just log it
        logger.info(f"Agent execution - Workflow: {workflow_name}, "
                   f"Input: {input_data}, Output: {output_data}")
    except Exception as e:
        logger.error(f"Failed to log agent execution: {e}")


@router.get("/available", dependencies=[Depends(require_permission("agents:configure"))])
async def get_available_agents():
    """
    Get list of available agents/workflows.
    Requires agents:configure permission (typically for admins/managers).
    """
    # In a real implementation, this might query n8n's API for available workflows
    # For now, return a static list based on the agent specs from the brief
    return {
        "agents": [
            {
                "name": "lead-scorer",
                "description": "Scores and routes incoming leads",
                "trigger": "webhook",
                "permissions_required": ["agents:trigger"]
            },
            {
                "name": "followup-sequencer",
                "description": "Automates follow-up sequences for leads",
                "trigger": "webhook",
                "permissions_required": ["agents:trigger"]
            },
            {
                "name": "content-engine",
                "description": "Generates marketing content and calendars",
                "trigger": "webhook",
                "permissions_required": ["agents:trigger"]
            },
            {
                "name": "student-onboarding",
                "description": "Automates student onboarding process",
                "trigger": "webhook",
                "permissions_required": ["agents:trigger"]
            },
            {
                "name": "support-bot",
                "description": "Handles student support inquiries",
                "trigger": "webhook",
                "permissions_required": ["agents:trigger"]
            },
            {
                "name": "ceo-briefing",
                "description": "Generates daily executive briefing for CEO",
                "trigger": "cron",
                "permissions_required": ["agents:trigger"]
            }
        ]
    }