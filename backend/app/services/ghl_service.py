# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/ghl_service.py
"""
GoHighLevel service client.

This service handles all interactions with GoHighLevel (GHL) CRM.
It never stores lead/contact data locally - all reads/writes go directly to GHL.
"""
import os
import httpx
import logging
import re
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

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/contacts/",
                    params={"locationId": self.location_id, "limit": limit},
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json().get("contacts", [])
        except Exception as exc:
            logger.error(f"Error fetching contacts from GHL: {exc}")
            return []

    async def get_all_contacts(self) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fetch the contact inventory using GHL cursor pagination."""
        if not self.private_token or not self.location_id:
            return [], {"status": "not_configured"}

        contacts: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        pages = 0

        try:
            async with httpx.AsyncClient() as client:
                while pages < settings.GHL_CONTACT_MAX_PAGES:
                    params: Dict[str, Any] = {
                        "locationId": self.location_id,
                        "limit": 100,
                    }
                    if cursor:
                        params["startAfterId"] = cursor

                    response = await client.get(
                        f"{self.base_url}/contacts/",
                        params=params,
                        headers=self.headers,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    page = data.get("contacts", [])
                    contacts.extend(page)
                    pages += 1

                    meta = data.get("meta", {}) or {}
                    next_cursor = meta.get("startAfterId") or data.get("startAfterId")
                    if not page or not next_cursor or next_cursor == cursor or len(page) < 100:
                        break
                    cursor = next_cursor

            return contacts, {
                "status": "connected",
                "pages": pages,
                "max_pages_reached": pages >= settings.GHL_CONTACT_MAX_PAGES,
            }

        except Exception as exc:
            logger.error(f"Error fetching paginated contacts from GHL: {exc}")
            return contacts, {
                "status": "error",
                "pages": pages,
                "error": "Contact inventory unavailable",
            }

    @staticmethod
    def normalize_contact(contact: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize identity, source, and contact channels without mutating GHL data."""
        first_name = " ".join(str(contact.get("firstName") or "").split())
        last_name = " ".join(str(contact.get("lastName") or "").split())
        name = " ".join(str(contact.get("name") or "").split()) or " ".join(part for part in [first_name, last_name] if part)
        email = str(contact.get("email") or "").strip().lower()
        phone = re.sub(r"\D", "", str(contact.get("phone") or ""))
        source = " ".join(str(contact.get("source") or "unknown").strip().lower().split())
        identity_key = f"email:{email}" if email else f"phone:{phone}" if phone else f"name:{name.lower()}|source:{source}"
        return {
            **contact,
            "firstName": first_name,
            "lastName": last_name,
            "name": name,
            "email": email,
            "phone": phone,
            "source": source,
            "identity_key": identity_key,
        }

    @classmethod
    def build_contact_quality_report(cls, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return duplicate, normalization, and missing-channel findings for review."""
        normalized = [cls.normalize_contact(contact) for contact in contacts]
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for contact in normalized:
            groups.setdefault(contact["identity_key"], []).append(contact)
        duplicate_groups = [
            {"identity_key": key, "contact_ids": [str(item.get("id")) for item in items], "count": len(items)}
            for key, items in groups.items()
            if key and not key.startswith("name:unknown") and len(items) > 1
        ]
        missing_channels = [str(contact.get("id")) for contact in normalized if not contact.get("email") and not contact.get("phone")]
        missing_sources = [str(contact.get("id")) for contact in normalized if contact.get("source") == "unknown"]
        return {
            "contacts_checked": len(normalized),
            "duplicate_groups": duplicate_groups,
            "duplicate_contacts": sum(group["count"] for group in duplicate_groups),
            "missing_contact_channel": len(missing_channels),
            "missing_source": len(missing_sources),
            "missing_contact_channel_ids": missing_channels[:100],
            "missing_source_ids": missing_sources[:100],
            "quality_status": "healthy" if not duplicate_groups and not missing_channels and not missing_sources else "needs_review",
        }

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

    async def add_contact_note(self, contact_id: str, body: str) -> bool:
        """Record an operational outcome as a note on the GHL contact."""
        if not self.private_token or not self.location_id:
            logger.warning("GHL credentials not configured - cannot add contact note")
            return False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/contacts/{contact_id}/notes",
                    params={"locationId": self.location_id},
                    json={"body": body},
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return True
        except Exception as exc:
            logger.error(f"Error adding note to GHL contact {contact_id}: {exc}")
            return False

    async def sync_enrollment_outcome(
        self,
        contact_id: str,
        *,
        queue_status: str | None = None,
        score: int | None = None,
        category: str | None = None,
        owner_id: str | None = None,
        lifecycle_stage: str | None = None,
        note: str | None = None,
    ) -> Dict[str, Any]:
        """Write one auditable Enrollment outcome to GHL.

        Score/category tags, queue status, and the app owner reference are written
        together. The optional note is recorded separately because GHL exposes
        notes through its contact notes endpoint rather than contact update.
        """
        tags: list[str] = []
        if category:
            tags.extend(["eny-enrollment", f"eny-score-{category}"])
        if queue_status:
            tags.append(f"eny-status-{queue_status}")
        if owner_id:
            tags.append(f"eny-owner-{owner_id}")
        if lifecycle_stage:
            tags.append(f"eny-lifecycle-{lifecycle_stage}")

        custom_fields: list[dict[str, Any]] = []
        if score is not None and settings.GHL_SALES_SCORE_FIELD_ID:
            custom_fields.append({"id": settings.GHL_SALES_SCORE_FIELD_ID, "value": score})
        if category and settings.GHL_SCORE_CATEGORY_FIELD_ID:
            custom_fields.append({"id": settings.GHL_SCORE_CATEGORY_FIELD_ID, "value": category})
        if queue_status and settings.GHL_ENROLLMENT_STATUS_FIELD_ID:
            custom_fields.append({"id": settings.GHL_ENROLLMENT_STATUS_FIELD_ID, "value": queue_status})
        if owner_id and settings.GHL_ENROLLMENT_OWNER_FIELD_ID:
            custom_fields.append({"id": settings.GHL_ENROLLMENT_OWNER_FIELD_ID, "value": owner_id})
        if lifecycle_stage and settings.GHL_ENROLLMENT_LIFECYCLE_FIELD_ID:
            custom_fields.append({"id": settings.GHL_ENROLLMENT_LIFECYCLE_FIELD_ID, "value": lifecycle_stage})

        payload: Dict[str, Any] = {}
        if custom_fields:
            payload["customFields"] = custom_fields
        if tags:
            contact = await self.get_contact(contact_id)
            if not contact:
                return {"success": False, "contact_updated": False, "note_recorded": False, "error": "Contact not found in GHL"}
            payload["tags"] = list(dict.fromkeys((contact.get("tags") or []) + tags))
        contact_updated = await self.update_contact(contact_id, payload) if payload else True
        note_recorded = await self.add_contact_note(contact_id, note) if note else True
        return {
            "success": contact_updated and note_recorded,
            "contact_updated": contact_updated,
            "note_recorded": note_recorded,
            "tags": tags,
            "fields_written": [field["id"] for field in custom_fields],
            "error": None if contact_updated and note_recorded else "GHL write-back incomplete",
        }

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
                "recent_activities": [],
                "opportunities": [],
                "stages": [],
            }

        try:
            opportunity_headers = {**self.headers, "Version": "v3"}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/opportunities/search",
                    params={"locationId": self.location_id, "status": "all", "limit": 100},
                    headers=opportunity_headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            opportunities = data.get("opportunities", [])
            total_leads = len(opportunities)
            won_opportunities = [
                opportunity for opportunity in opportunities
                if str(opportunity.get("status", "")).lower() == "won"
            ]
            conversion_rate = len(won_opportunities) / total_leads if total_leads else 0.0
            stage_counts: Dict[str, int] = {}
            for opportunity in opportunities:
                stage_name = (
                    opportunity.get("pipelineStageName")
                    or opportunity.get("stageName")
                    or opportunity.get("status")
                    or "Unassigned"
                )
                stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
            stages = [
                {
                    "id": str(index),
                    "name": name,
                    "description": "Live GoHighLevel opportunity stage",
                    "count": count,
                    "percentage": round((count / total_leads) * 100, 1) if total_leads else 0,
                    "color": "brass",
                }
                for index, (name, count) in enumerate(stage_counts.items(), start=1)
            ]

            return {
                "total_leads": total_leads,
                "conversion_rate": conversion_rate,
                "revenue_forecast": sum(
                    float(opportunity.get("expectedValue", 0) or 0)
                    for opportunity in opportunities
                ),
                "at_risk_deals": len([
                    opportunity for opportunity in opportunities
                    if str(opportunity.get("status", "")).lower()
                    in {"stalled", "negotiation"}
                ]),
                "sources_breakdown": {},
                "recent_activities": [],
                "opportunities": opportunities,
                "stages": stages,
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
                "opportunities": [],
                "stages": [],
                "error": "Pipeline data unavailable",
            }

    async def get_ai_context(self, include_pipeline: bool = True) -> Dict[str, Any]:
        """Build a minimized CRM snapshot for role-aware Claude prompts."""
        contacts, inventory_status = await self.get_all_contacts()
        scored_leads = []
        score_distribution = {"hot": 0, "warm": 0, "follow-up": 0, "cold": 0, "unclassified": 0}
        sources_breakdown: Dict[str, int] = {}
        scored_sources_breakdown: Dict[str, int] = {}
        unscored_contacts = 0

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
            source = contact.get("source") or "unknown"
            sources_breakdown[source] = sources_breakdown.get(source, 0) + 1
            if score_value is None and not category:
                unscored_contacts += 1
                continue

            try:
                score = float(score_value) if score_value is not None else None
            except (TypeError, ValueError):
                score = None

            normalized_category = str(category or "").strip().lower()
            if not normalized_category and score is not None:
                if score >= 85:
                    normalized_category = "hot"
                elif score >= 70:
                    normalized_category = "warm"
                elif score >= 50:
                    normalized_category = "follow-up"
                else:
                    normalized_category = "cold"
            if normalized_category not in score_distribution:
                normalized_category = "unclassified"
            score_distribution[normalized_category] += 1
            scored_sources_breakdown[source] = scored_sources_breakdown.get(source, 0) + 1

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
            "contact_inventory": inventory_status,
            "scored_contacts": len(scored_leads),
            "unscored_contacts": unscored_contacts,
            "leads_available": bool(scored_leads),
            "scored_leads": scored_leads[:20],
            "score_distribution": score_distribution,
            "contacts_source_breakdown": sources_breakdown,
            "scored_leads_source_breakdown": scored_sources_breakdown,
        }
        if include_pipeline:
            context["pipeline"] = await self.get_pipeline_data()
        return context

    async def get_cohort_inventory(self) -> Dict[str, Any]:
        """Return privacy-minimized source/tag groups for human-reviewed cohorting."""
        contacts, inventory_status = await self.get_all_contacts()
        source_groups: Dict[str, Dict[str, Any]] = {}
        unscored_samples: List[Dict[str, Any]] = []

        for contact in contacts:
            source = contact.get("source") or "unknown"
            group = source_groups.setdefault(source, {"source": source, "count": 0, "unscored_count": 0, "tags": {}})
            group["count"] += 1
            for tag in contact.get("tags", [])[:10]:
                group["tags"][tag] = group["tags"].get(tag, 0) + 1

            custom_fields = contact.get("customFields", [])
            if isinstance(custom_fields, dict):
                custom_fields = [custom_fields]
            field_ids = {field.get("id") for field in custom_fields if isinstance(field, dict)}
            field_values = {
                str(field.get("id")): field.get("value")
                for field in custom_fields
                if isinstance(field, dict) and field.get("id") is not None
            }
            field_values.update({
                str(field.get("fieldKey") or field.get("key")): field.get("value")
                for field in custom_fields
                if isinstance(field, dict) and (field.get("fieldKey") or field.get("key"))
            })
            has_score = field_values.get(settings.GHL_SALES_SCORE_FIELD_ID) not in (None, "")
            has_score = has_score or field_values.get("contact.sales_score") not in (None, "")
            has_category = field_values.get(settings.GHL_SCORE_CATEGORY_FIELD_ID) not in (None, "")
            has_category = has_category or field_values.get("contact.score_category") not in (None, "")
            if not has_score and not has_category:
                group["unscored_count"] += 1
                if len(unscored_samples) < 30:
                    unscored_samples.append({
                        "id": contact.get("id"),
                        "source": source,
                        "tags": contact.get("tags", [])[:10],
                        "created_at": contact.get("dateAdded"),
                    })

        return {
            "inventory": inventory_status,
            "total_contacts": len(contacts),
            "source_groups": list(source_groups.values()),
            "unscored_sample": unscored_samples,
        }

    async def get_unscored_source_contacts(self, source_filter: str, limit: int) -> List[Dict[str, Any]]:
        """Return unscored contacts for an explicitly approved source cohort."""
        contacts, _ = await self.get_all_contacts()
        normalized_filter = " ".join(source_filter.strip().lower().split())
        selected = []
        for contact in contacts:
            source = " ".join(str(contact.get("source") or "unknown").strip().lower().split())
            tags = {
                " ".join(str(tag).strip().lower().split())
                for tag in (contact.get("tags") or [])
            }
            source_matches = (
                source == normalized_filter
                or normalized_filter in source
                or source in normalized_filter
                or normalized_filter in tags
            )
            if not source_matches:
                continue
            custom_fields = contact.get("customFields", [])
            if isinstance(custom_fields, dict):
                custom_fields = [custom_fields]
            field_values: Dict[str, Any] = {}
            for field in custom_fields:
                if not isinstance(field, dict):
                    continue
                value = field.get("value")
                if field.get("id") is not None:
                    field_values[str(field["id"])] = value
                field_key = field.get("fieldKey") or field.get("key")
                if field_key:
                    field_values[str(field_key)] = value
            score_value = field_values.get(settings.GHL_SALES_SCORE_FIELD_ID)
            score_value = score_value if score_value is not None else field_values.get("contact.sales_score")
            category_value = field_values.get(settings.GHL_SCORE_CATEGORY_FIELD_ID)
            category_value = category_value if category_value is not None else field_values.get("contact.score_category")
            if score_value not in (None, "") or category_value not in (None, ""):
                continue
            selected.append({
                "id": contact.get("id"),
                "name": contact.get("name") or " ".join(part for part in [contact.get("firstName"), contact.get("lastName")] if part),
                "source": contact.get("source"),
                "tags": contact.get("tags", []),
                "created_at": contact.get("dateAdded"),
            })
            if len(selected) >= limit:
                break
        return selected

    async def get_enrollment_leads(self, limit: int = 20, search: str = "") -> List[Dict[str, Any]]:
        """Return GHL contacts shaped for the Enrollment workspace without storing them locally."""
        contacts, _ = await self.get_all_contacts()
        normalized_search = search.strip().lower()
        leads: List[Dict[str, Any]] = []

        for contact in contacts:
            first_name = contact.get("firstName") or ""
            last_name = contact.get("lastName") or ""
            name = contact.get("name") or " ".join(part for part in [first_name, last_name] if part)
            email = contact.get("email") or ""
            phone = contact.get("phone") or ""
            haystack = " ".join([name, email, phone, contact.get("source") or ""]).lower()
            if normalized_search and normalized_search not in haystack:
                continue

            custom_fields = contact.get("customFields", [])
            if isinstance(custom_fields, dict):
                custom_fields = [custom_fields]
            fields: Dict[str, Any] = {}
            for field in custom_fields:
                if not isinstance(field, dict):
                    continue
                value = field.get("value")
                if field.get("id"):
                    fields[str(field["id"])] = value
                if field.get("fieldKey") or field.get("key"):
                    fields[str(field.get("fieldKey") or field.get("key"))] = value

            score_value = fields.get(settings.GHL_SALES_SCORE_FIELD_ID)
            category = fields.get(settings.GHL_SCORE_CATEGORY_FIELD_ID)
            try:
                score = int(float(score_value)) if score_value is not None else None
            except (TypeError, ValueError):
                score = None
            if not category and score is not None:
                category = "hot" if score >= 85 else "warm" if score >= 70 else "follow-up" if score >= 50 else "cold"

            leads.append({
                "id": contact.get("id"),
                "firstName": first_name,
                "lastName": last_name,
                "name": name,
                "email": email,
                "phone": contact.get("phone"),
                "score": score,
                "category": category,
                "source": contact.get("source"),
                "tags": contact.get("tags", []),
                "updated_at": contact.get("dateUpdated"),
            })
            if len(leads) >= limit:
                break

        return leads


# Create a singleton instance for use in the application
ghl_service = GHLService()
