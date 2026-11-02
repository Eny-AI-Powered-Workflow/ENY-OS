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
        workshop_name: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger an n8n workshop by name via webhook.

        Args:
            workshop_name: The name of the workshop to trigger (e.g., "lead-scorer")
            data: The data to send to the workshop webhook

        Returns:
            The response from the n8n workshop execution
        """
        # In a real implementation, we would have a mapping from workshop names to webhook URLs
        # For now, we'll construct a webhook URL based on the workshop name
        webhook_url = f"{self.base_url}/webhook/{workshop_name}"

        # Mock fallback for development
        if not self.api_key:
            logger.info(f"Mock: Triggering n8n workshop '{workshop_name}' with data: {data}")
            # Simulate some processing time
            await asyncio.sleep(0.1)

            # Return mock response based on workshop type
            if "lead-scorer" in workshop_name:
                return {
                    "status": "success",
                    "workshop": workshop_name,
                    "score": 85,
                    "tags": ["hot", "follow-up"],
                    "message": "Workshop scored successfully"
                }
            elif "followup" in workshop_name:
                return {
                    "status": "success",
                    "workshop": workshop_name,
                    "actions_taken": ["email_sent", "sms_scheduled"],
                    "message": "Follow-up sequence initiated"
                }
            else:
                return {
                    "status": "success",
                    "workshop": workshop_name,
                    "message": f"Workshop {workshop_name} executed successfully"
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
            logger.error(f"HTTP error triggering workshop {workshop_name}: {e}")
            return {
                "status": "error",
                "workshop": workshop_name,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Error triggering workshop {workshop_name}: {e}")
            return {
                "status": "error",
                "workshop": workshop_name,
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
            logger.info("Mock: Fetching workshop executions")
            return [
                {
                    "id": f"exec-{i}",
                    "workshopId": workshop_id or "workshop-1",
                    "status": "success" if i % 2 == 0 else "error",
                    "startedAt": f"2024-01-20T10:{i:02d}:00Z",
                    "finishedAt": f"2024-01-20T10:{i:02d}:05Z",
                }
                for i in range(limit)
            ]

        try:
            async with httpx.AsyncClient() as client:
                params = {"limit": limit}
                if workshop_id:
                    params["workshopId"] = workshop_id

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
            logger.error(f"Error fetching workshop executions: {e}")
            return []

    async def get_workflow(self, workshop_name: str) -> Optional[Dict[str, Any]]:
        """
        Get workshop details by name.
        """
        if not self.api_key:
            logger.info(f"Mock: Fetching workshop {workshop_name}")
            return {
                "id": f"workshop-{hash(workshop_name) % 1000}",
                "name": workshop_name,
                "active": True,
                "nodes": [],
                "connections": {},
                "createdAt": "2024-01-15T10:30:00Z",
                "updatedAt": "2024-01-20T14:22:00Z",
            }

        try:
            async with httpx.AsyncClient() as client:
                # First get all workshops to find the one by name
                response = await client.get(
                    f"{self.base_url}/workshops",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                # Find workshop by name
                workshops = data.get("data", [])
                for workshop in workshops:
                    if workshop.get("name") == workshop_name:
                        return workshop

                return None
        except Exception as e:
            logger.error(f"Error fetching workshop {workshop_name}: {e}")
            return None