# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/agents.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import Dict, Any
import json
from app.api.deps import require_permission
from app.services.n8n_service import N8NService
from app.services.ghl_service import GHLService
from app.models.audit_log import AuditLog
from app.models.agent_log import AgentLog
from app.db.session import get_db
from app.core.security import get_current_user
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
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
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

        # Log the agent execution to agent_logs table
        result_status = result.get("status") if isinstance(result, dict) else None
        execution_status = "error" if result_status == "error" else "success"
        agent_log = AgentLog(
            workflow_name=workflow_name,
            user_id=str(current_user["id"]) if isinstance(current_user, dict) and "id" in current_user else str(current_user.id),
            input_data=json.dumps(data),
            output_data=json.dumps(result),
            status=execution_status
        )
        db.add(agent_log)
        db.commit()

        if execution_status == "error":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": "n8n workflow execution failed",
                    "workflow": workflow_name,
                    "result": result,
                },
            )

        response_status = "error" if execution_status == "error" else "success"
        return {
            "status": response_status,
            "workflow": workflow_name,
            "result": result
        }

    except Exception as e:
        logger.error(f"Failed to trigger workflow {workflow_name}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger workflow: {str(e)}"
        )


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
                "name": "ENY-SALES-SCORE",
                "description": "Lead scoring workflow",
                "trigger": "webhook",
                "nodes": ["Claude API", "GHL Contact Update", "Slack Notification"]
            }
        ]
    }
