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

from app.core.config import settings

logger = logging.getLogger(__name__)


class GHLService:
    def __init__(self):
        self.base_url = settings.GHL_BASE_URL
        self.private_token = settings.GHL_PRIVATE_TOKEN
        self.location_id = settings.GHL_LOCATION_ID

        if not self.private_token:
            logger.warning("GHL_PRIVATE_TOKEN not set - GHL service will not function")
        if not self.location_id:
            logger.warning("GHL_LOCATION_ID not set - GHL service may have limited functionality")

        self.headers = {
            "Authorization": f"Bearer {self.private_token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        } if self.private_token else {}

    async def get_contacts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get contacts from GHL.
        Returns empty list if credentials are not configured.
        """
        # Return empty list if credentials are not configured
        if not self.private_token or not self.location_id:
            logger.warning("GHL credentials not configured - returning empty contacts list")
            return []

        # Real GHL API call
        try:
            async with httpx.AsyncClient() as client:
                params = {"limit": limit}
                # Note: GHL API seems to not accept offset parameter directly
                # Using limit only for now; offset-based pagination may need cursor approach
                if self.location_id:
                    params["locationId"] = self.location_id
                response = await client.get(
                    f"{self.base_url}/contacts/",
                    params=params,
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
        """Get a single contact by ID from GHL."""
        # Return None if credentials are not configured
        if not self.private_token or not self.location_id:
            logger.warning("GHL credentials not configured - cannot fetch contact")
            return None

        try:
            async with httpx.AsyncClient() as client:
                params = {}
                if self.location_id:
                    params["locationId"] = self.location_id
                response = await client.get(
                    f"{self.base_url}/contacts/{contact_id}",
                    params=params,
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
        # Return False if credentials are not configured
        if not self.private_token or not self.location_id:
            logger.warning("GHL credentials not configured - cannot tag contact")
            return False

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

                params = {}
                if self.location_id:
                    params["locationId"] = self.location_id
                response = await client.put(
                    f"{self.base_url}/contacts/{contact_id}",
                    params=params,
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
        # Return False if credentials are not configured
        if not self.private_token or not self.location_id:
            logger.warning("GHL credentials not configured - cannot update contact")
            return False

        try:
            async with httpx.AsyncClient() as client:
                params = {}
                if self.location_id:
                    params["locationId"] = self.location_id
                response = await client.put(
                    f"{self.base_url}/contacts/{contact_id}",
                    params=params,
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
        Returns default empty structure if credentials are not configured.
        """
        # Return empty structure if credentials are not configured
        if not self.private_token or not self.location_id:
            logger.warning("GHL credentials not configured - returning empty pipeline data")
            return {
                "total_leads": 0,
                "conversion_rate": 0.0,
                "revenue_forecast": 0,
                "at_risk_deals": 0,
                "sources_breakdown": {},
                "recent_activities": []
            }

    async def get_ai_context(self, include_pipeline: bool = True) -> Dict[str, Any]:
        """Build a minimized CRM snapshot for role-aware Claude prompts."""
        contacts = await self.get_contacts(limit=100)
        scored_leads = []

        for contact in contacts:
            custom_fields = contact.get("customFields", [])
            fields = {
                field.get("id"): field.get("value")
                for field in custom_fields
                if field.get("id")
            }
            score_value = fields.get("caiccVdZ41m5BMyWMH57")
            category = fields.get("CiowYO5hnAmwWKCp7vAO")
            if score_value is None and not category:
                continue

            try:
                score = float(score_value) if score_value is not None else None
            except (TypeError, ValueError):
                score = None

            scored_leads.append({
                "id": contact.get("id"),
                "name": contact.get("name") or " ".join(
                    part for part in [contact.get("firstName"), contact.get("lastName")] if part
                ),
                "score": score,
                "category": category,
                "source": contact.get("source"),
                "tags": contact.get("tags", []),
                "updated_at": contact.get("dateUpdated"),
            })

        scored_leads.sort(key=lambda lead: lead.get("score") or 0, reverse=True)
        context: Dict[str, Any] = {
            "source": "GoHighLevel",
            "leads_available": bool(contacts),
            "scored_leads": scored_leads[:20],
        }
        if include_pipeline:
            context["pipeline"] = await self.get_pipeline_data()
        return context

        # Real GHL API call for opportunities
        try:
            async with httpx.AsyncClient() as client:
                params = {}
                if self.location_id:
                    params["locationId"] = self.location_id
                # Note: GHL API endpoints for pipelines may vary
                # This is a placeholder implementation
                response = await client.get(
                    f"{self.base_url}/opportunities/",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                # Process and return pipeline data in expected format
                opportunities = data.get("opportunities", [])
                total_leads = len(opportunities)
                won_opportunities = [opp for opp in opportunities if opp.get("pipelineStage") == "won"]
                conversion_rate = len(won_opportunities) / total_leads if total_leads > 0 else 0.0

                return {
                    "total_leads": total_leads,
                    "conversion_rate": conversion_rate,
                    "revenue_forecast": sum(float(opp.get("expectedValue", 0)) for opp in opportunities),
                    "at_risk_deals": len([opp for opp in opportunities if opp.get("pipelineStage") in ["stalled", "negotiation"]]),
                    "sources_breakdown": {},  # Would need additional API calls to implement
                    "recent_activities": []   # Would need additional API calls to implement
                }
        except Exception as e:
            logger.error(f"Error fetching pipeline data from GHL: {e}")
            # Return empty structure on error
            return {
                "total_leads": 0,
                "conversion_rate": 0.0,
                "revenue_forecast": 0,
                "at_risk_deals": 0,
                "sources_breakdown": {},
                "recent_activities": []
            }


# Create a singleton instance for use in the application
ghl_service = GHLService()
