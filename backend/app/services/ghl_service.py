# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/ghl_service.py
"""
GoHighLevel service client.

This service handles all interactions with GoHighLevel (GHL) CRM.
It never stores lead/contact data locally - all reads/writes go directly to GHL.
"""
import os
import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class GHLService:
    def __init__(self):
        self.base_url = os.getenv("GHL_BASE_URL", "https://services.leadconnectorhq.com")
        self.private_token = os.getenv("GHL_PRIVATE_TOKEN")
        self.location_id = os.getenv("GHL_LOCATION_ID")

        if not self.private_token:
            logger.warning("GHL_PRIVATE_TOKEN not set - using mock mode")
        if not self.location_id:
            logger.warning("GHL_LOCATION_ID not set - using mock mode")

        self.headers = {
            "Authorization": f"Bearer {self.private_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        } if self.private_token else {}

    async def get_contacts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get contacts from GHL.
        Returns mock data if credentials are not configured.
        """
        # Mock fallback for development
        if not self.private_token or not self.location_id:
            logger.info("Using mock GHL data")
            return [
                {
                    "id": "mock-contact-1",
                    "firstName": "John",
                    "lastName": "Doe",
                    "email": "john.doe@example.com",
                    "phone": "+1234567890",
                    "source": "Website",
                    "tags": ["lead", "new"],
                    "dateAdded": "2024-01-15T10:30:00Z",
                },
                {
                    "id": "mock-contact-2",
                    "firstName": "Jane",
                    "lastName": "Smith",
                    "email": "jane.smith@example.com",
                    "phone": "+1234567891",
                    "source": "Referral",
                    "tags": ["qualified", "hot"],
                    "dateAdded": "2024-01-14T15:45:00Z",
                }
            ][:limit]

        # Real GHL API call
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/contacts/",
                    params={"limit": limit, "offset": offset},
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("contacts", [])
        except Exception as e:
            logger.error(f"Error fetching contacts from GHL: {e}")
            # Return empty list on error to avoid breaking the flow
            return []

    async def get_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get a single contact by ID."""
        if not self.private_token or not self.location_id:
            # Mock data
            return {
                "id": contact_id,
                "firstName": "Mock",
                "lastName": "User",
                "email": "mock@example.com",
                "phone": "+1234567890",
                "source": "Mock",
                "tags": ["mock"],
                "dateAdded": "2024-01-15T10:30:00Z",
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/contacts/{contact_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching contact {contact_id} from GHL: {e}")
            return None

    async def tag_contact(self, contact_id: str, tags: List[str]) -> bool:
        """
        Add tags to a contact in GHL.
        Returns True if successful, False otherwise.
        """
        if not self.private_token or not self.location_id:
            logger.info(f"Mock: Tagging contact {contact_id} with {tags}")
            return True

        try:
            async with httpx.AsyncClient() as client:
                # First get the contact to see current tags
                contact = await self.get_contact(contact_id)
                if not contact:
                    logger.error(f"Contact {contact_id} not found")
                    return False

                current_tags = contact.get("tags", [])
                # Merge tags, avoiding duplicates
                new_tags = list(set(current_tags + tags))

                response = await client.put(
                    f"{self.base_url}/contacts/{contact_id}",
                    json={"tags": new_tags},
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Error tagging contact {contact_id} in GHL: {e}")
            return False

    async def update_contact(self, contact_id: str, data: Dict[str, Any]) -> bool:
        """Update contact fields in GHL."""
        if not self.private_token or not self.location_id:
            logger.info(f"Mock: Updating contact {contact_id} with {data}")
            return True

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/contacts/{contact_id}",
                    json=data,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Error updating contact {contact_id} in GHL: {e}")
            return False

    async def get_pipeline_data(self) -> Dict[str, Any]:
        """
        Get pipeline/opportunities data from GHL.
        Returns mock data if credentials are not configured.
        """
        # Mock fallback for development
        if not self.private_token or not self.location_id:
            logger.info("Using mock GHL pipeline data")
            return {
                "total_leads": 150,
                "conversion_rate": 0.25,
                "revenue_forecast": 75000,
                "at_risk_deals": 12,
                "sources_breakdown": {
                    "Website": 45,
                    "Referral": 30,
                    "Social Media": 25,
                    "Events": 15,
                    "Other": 10
                },
                "recent_activities": [
                    {
                        "id": "activity-1",
                        "type": "email_sent",
                        "contact_id": "contact-1",
                        "timestamp": "2024-01-20T09:15:00Z",
                        "description": "Sent follow-up email to John Doe"
                    },
                    {
                        "id": "activity-2",
                        "type": "call_completed",
                        "contact_id": "contact-2",
                        "timestamp": "2024-01-20T10:30:00Z",
                        "description": "Completed discovery call with Jane Smith"
                    }
                ]
            }

        # Real GHL API call for pipelines/opportunities
        try:
            async with httpx.AsyncClient() as client:
                # Note: GHL API endpoints for pipelines may vary
                # This is a placeholder implementation
                response = await client.get(
                    f"{self.base_url}/opportunities/",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                # Process and return pipeline data in expected format
                opportunities = data.get("opportunities", [])
                total_leads = len(opportunities)
                won_opportunities = [opp for opp in opportunities if opp.get("pipelineStage") == "won"]
                conversion_rate = len(won_opportunities) / total_leads if total_leads > 0 else 0

                return {
                    "total_leads": total_leads,
                    "conversion_rate": conversion_rate,
                    "revenue_forecast": sum(float(opp.get("expectedValue", 0)) for opp in opportunities),
                    "at_risk_deals": len([opp for opp in opportunities if opp.get("pipelineStage") in ["stalled", "negotiation"]]),
                    "sources_breakdown": {},  # Would need to implement source breakdown
                    "recent_activities": []   # Would need to fetch activities separately
                }
        except Exception as e:
            logger.error(f"Error fetching pipeline data from GHL: {e}")
            # Return mock data on error for graceful degradation
            return {
                "total_leads": 0,
                "conversion_rate": 0,
                "revenue_forecast": 0,
                "at_risk_deals": 0,
                "sources_breakdown": {},
                "recent_activities": []
            }


# Create a singleton instance for use in the application
ghl_service = GHLService()