# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/n8n_service.py
"""
n8n service client.

This service handles triggering n8n workflows via webhooks.
n8n owns the automation logic; this service just triggers workflows.
"""
import os
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class N8NService:
    def __init__(self):
        self.base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        self.api_key = os.getenv("N8N_API_KEY")

        if not self.api_key:
            logger.warning("N8N_API_KEY not set - using mock mode")

        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["X-N8N-API-KEY"] = self.api_key

    async def trigger_workflow(
        self,
        workflow_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger an n8n workflow by name via webhook.

        Args:
            workflow_name: The name of the workflow to trigger (e.g., "lead-scorer")
            data: The data to send to the workflow webhook

        Returns:
            The response from the n8n workflow execution
        """
        # In a real implementation, we would have a mapping from workflow names to webhook URLs
        # For now, we'll construct a webhook URL based on the workflow name
        webhook_url = f"{self.base_url}/webhook/{workflow_name}"

        # Mock fallback for development
        if not self.api_key:
            logger.info(f"Mock: Triggering n8n workflow '{workflow_name}' with data: {data}")
            # Simulate some processing time
            import asyncio
            await asyncio.sleep(0.1)

            # Return mock response based on workflow type
            if "lead-scorer" in workflow_name:
                return {
                    "status": "success",
                    "workflow": workflow_name,
                    "score": 85,
                    "tags": ["hot", "follow-up"],
                    "message": "Lead scored successfully"
                }
            elif "followup" in workflow_name:
                return {
                    "status": "success",
                    "workflow": workflow_name,
                    "actions_taken": ["email_sent", "sms_scheduled"],
                    "message": "Follow-up sequence initiated"
                }
            else:
                return {
                    "status": "success",
                    "workflow": workflow_name,
                    "message": f"Workflow {workflow_name} executed successfully"
                }

        # Real n8n API call
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=data,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error triggering workflow {workflow_name}: {e}")
            return {
                "status": "error",
                "workflow": workflow_name,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Error triggering workflow {workflow_name}: {e}")
            return {
                "status": "error",
                "workflow": workflow_name,
                "error": str(e)
            }

    async def get_workflow_executions(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get workflow executions from n8n.
        """
        if not self.api_key:
            logger.info("Mock: Fetching workflow executions")
            return [
                {
                    "id": f"exec-{i}",
                    "workflowId": workflow_id or "workflow-1",
                    "status": "success" if i % 2 == 0 else "error",
                    "startedAt": f"2024-01-20T10:{i:02d}:00Z",
                    "finishedAt": f"2024-01-20T10:{i:02d}:05Z",
                }
                for i in range(limit)
            ]

        try:
            async with httpx.AsyncClient() as client:
                params = {"limit": limit}
                if workflow_id:
                    params["workflowId"] = workflow_id

                response = await client.get(
                    f"{self.base_url}/executions",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching workflow executions: {e}")
            return []

    async def get_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow details by name.
        """
        if not self.api_key:
            logger.info(f"Mock: Fetching workflow {workflow_name}")
            return {
                "id": f"workflow-{hash(workflow_name) % 1000}",
                "name": workflow_name,
                "active": True,
                "nodes": [],
                "connections": {},
                "createdAt": "2024-01-15T10:30:00Z",
                "updatedAt": "2024-01-20T14:22:00Z",
            }

        try:
            async with httpx.AsyncClient() as client:
                # First get all workflows to find the one by name
                response = await client.get(
                    f"{self.base_url}/workflows",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                # Find workflow by name
                workflows = data.get("data", [])
                for workflow in workflows:
                    if workflow.get("name") == workflow_name:
                        return workflow

                return None
        except Exception as e:
            logger.error(f"Error fetching workflow {workflow_name}: {e}")
            return None