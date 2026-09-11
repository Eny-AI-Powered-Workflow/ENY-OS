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

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/opportunities/",
                    params={"locationId": self.location_id},
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            opportunities = data.get("opportunities", [])
            total_leads = len(opportunities)
            won_opportunities = [
                opportunity for opportunity in opportunities
                if str(opportunity.get("pipelineStage", "")).lower() == "won"
            ]
            conversion_rate = len(won_opportunities) / total_leads if total_leads else 0.0

            return {
                "total_leads": total_leads,
                "conversion_rate": conversion_rate,
                "revenue_forecast": sum(
                    float(opportunity.get("expectedValue", 0) or 0)
                    for opportunity in opportunities
                ),
                "at_risk_deals": len([
                    opportunity for opportunity in opportunities
                    if str(opportunity.get("pipelineStage", "")).lower()
                    in {"stalled", "negotiation"}
                ]),
                "sources_breakdown": {},
                "recent_activities": [],
            }
        except Exception as exc:
            logger.error(f"Error fetching pipeline data from GHL: {exc}")
            return {
                "total_leads": 0,
                "conversion_rate": 0.0,
                "revenue_forecast": 0,
                "at_risk_deals": 0,
                "sources_breakdown": {},
                "recent_activities": [],
                "error": "Pipeline data unavailable",
            }

    async def get_ai_context(self, include_pipeline: bool = True) -> Dict[str, Any]:
        """Build a minimized CRM snapshot for role-aware Claude prompts."""
        contacts = await self.get_contacts(limit=100)
        scored_leads = []
        score_distribution = {"hot": 0, "warm": 0, "follow-up": 0, "cold": 0, "unclassified": 0}
        sources_breakdown: Dict[str, int] = {}

        for contact in contacts:
            custom_fields = contact.get("customFields", [])
            if isinstance(custom_fields, dict):
                custom_fields = [custom_fields]

            fields = {}
            for field in custom_fields:
                if not isinstance(field, dict):
                    continue
                field_id = field.get("id")
                field_key = field.get("fieldKey") or field.get("key")
                value = field.get("value")
                if field_id:
                    fields[field_id] = value
                if field_key:
                    fields[field_key] = value

            score_value = fields.get(settings.GHL_SALES_SCORE_FIELD_ID)
            score_value = score_value if score_value is not None else fields.get("contact.sales_score")
            category = fields.get(settings.GHL_SCORE_CATEGORY_FIELD_ID)
            category = category if category is not None else fields.get("contact.score_category")
            if score_value is None and not category:
                continue

            try:
                score = float(score_value) if score_value is not None else None
            except (TypeError, ValueError):
                score = None

            normalized_category = str(category or "").strip().lower()
            if normalized_category not in score_distribution:
                normalized_category = "unclassified"
            score_distribution[normalized_category] += 1
            source = contact.get("source") or "unknown"
            sources_breakdown[source] = sources_breakdown.get(source, 0) + 1

            scored_leads.append({
                "id": contact.get("id"),
                "name": contact.get("name") or " ".join(
                    part for part in [contact.get("firstName"), contact.get("lastName")] if part
                ),
                "score": score,
                "category": category or normalized_category,
                "source": contact.get("source"),
                "tags": contact.get("tags", []),
                "updated_at": contact.get("dateUpdated"),
            })

        scored_leads.sort(key=lambda lead: lead.get("score") or 0, reverse=True)
        context: Dict[str, Any] = {
            "source": "GoHighLevel",
            "crm_status": "connected",
            "contacts_returned": len(contacts),
            "leads_available": bool(scored_leads),
            "scored_leads": scored_leads[:20],
            "score_distribution": score_distribution,
            "scored_leads_source_breakdown": sources_breakdown,
        }
        if include_pipeline:
            context["pipeline"] = await self.get_pipeline_data()
        return context


# Create a singleton instance for use in the application
ghl_service = GHLService()
