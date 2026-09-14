# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/n8n_service.py
"""
n8n service client.

This service handles triggering n8n workflows via webhooks.
n8n owns the automation logic; this service just triggers workflows.
"""
import os
import httpx
import logging
import asyncio
from typing import Dict, Any, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class N8NService:
    def __init__(self):
        self.base_url = settings.N8N_BASE_URL.rstrip("/")
        self.api_key = settings.N8N_API_KEY
        self.mock_mode = settings.N8N_MOCK_MODE

        if self.mock_mode:
            logger.warning("N8N_MOCK_MODE enabled - n8n calls are simulated")

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
        normalized_name = (workflow_name or "").strip().lower()
        webhook_url = f"{self.base_url}/webhook/{normalized_name}"

        allowed = {"eny-sales-score", "eny-enrollment-hot-leads"}
        if normalized_name not in allowed:
            return {
                "status": "error",
                "workflow": workflow_name,
                "error": "Workflow is not registered",
            }

        # Mock fallback for development
        if self.mock_mode:
            logger.info(f"Mock: Triggering n8n workflow '{workflow_name}' with data: {data}")
            # Simulate some processing time
            await asyncio.sleep(0.1)

            # Return mock response based on workflow type
            if normalized_name == "eny-sales-score":
                score = int(data.get("score", 85))
                return {
                    "status": "success",
                    "workflow": normalized_name,
                    "score": score,
                    "tags": ["hot", "follow-up"] if score >= 85 else ["warm", "follow-up"],
                    "message": "Workflow executed successfully"
                }
            if normalized_name == "eny-enrollment-hot-leads":
                return {
                    "status": "success",
                    "workflow": normalized_name,
                    "message": "Enrollment notification queued",
                    "notified": True,
                }
            return {
                "status": "success",
                "workflow": normalized_name,
                "message": f"Workflow {normalized_name} executed successfully"
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
        if self.mock_mode:
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
        if self.mock_mode:
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
