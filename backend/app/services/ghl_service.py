# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/ghl_service.py
"""
GoHighLevel service client.

This service handles all interactions with GoHighLevel (GHL) CRM.
It never stores lead/contact data locally - all reads/writes go directly to GHL.
"""
import asyncio
import httpx
import logging
import re
from datetime import date
from typing import Dict, Any, List, Optional
from urllib.parse import quote

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

    async def get_contacts_page(
        self,
        limit: int = 100,
        cursor_id: Optional[str] = None,
        cursor_after: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, str]]]:
        """Fetch one cursor-paginated contact page from GHL."""
        if not self.private_token or not self.location_id:
            raise RuntimeError("GHL_PRIVATE_TOKEN and GHL_LOCATION_ID must be configured to fetch leads")

        params: Dict[str, Any] = {"locationId": self.location_id, "limit": limit}
        if cursor_id:
            params["startAfterId"] = cursor_id
        if cursor_after:
            params["startAfter"] = cursor_after

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/contacts/",
                params=params,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        contacts = data.get("contacts", [])
        meta = data.get("meta", {}) or {}
        next_id = meta.get("startAfterId") or data.get("startAfterId")
        next_after = meta.get("startAfter") or data.get("startAfter")
        if not contacts or len(contacts) < limit:
            return contacts, None
        if not next_id and not next_after:
            raise RuntimeError("GHL returned a full contact page without a pagination cursor")
        return contacts, {
            **({"start_after_id": str(next_id)} if next_id else {}),
            **({"start_after": str(next_after)} if next_after else {}),
        }

    async def get_contacts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get contacts from GHL.
        Returns empty list if credentials are not configured.
        """
        try:
            contacts: List[Dict[str, Any]] = []
            cursor: Optional[Dict[str, str]] = None
            remaining = offset + limit
            while remaining > 0:
                page_size = min(100, remaining)
                page, cursor = await self.get_contacts_page(
                    page_size,
                    (cursor or {}).get("start_after_id"),
                    (cursor or {}).get("start_after"),
                )
                contacts.extend(page)
                remaining -= len(page)
                if not cursor or not page:
                    break
            return contacts[offset:offset + limit]
        except Exception as exc:
            logger.error(f"Error fetching contacts from GHL: {exc}")
            return []

    async def get_contacts_offset_page(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, str]]]:
        """Translate legacy offset pagination into GHL cursor requests."""
        cursor: Optional[Dict[str, str]] = None
        remaining = offset
        while remaining > 0:
            page_size = min(100, remaining)
            page, cursor = await self.get_contacts_page(
                page_size,
                (cursor or {}).get("start_after_id"),
                (cursor or {}).get("start_after"),
            )
            remaining -= len(page)
            if not page or not cursor:
                return [], None
        return await self.get_contacts_page(
            min(limit, 100),
            (cursor or {}).get("start_after_id"),
            (cursor or {}).get("start_after"),
        )

    async def get_all_contacts(self) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fetch the contact inventory using GHL cursor pagination."""
        if not self.private_token or not self.location_id:
            return [], {"status": "not_configured"}

        contacts: List[Dict[str, Any]] = []
        cursor: Optional[Dict[str, str]] = None
        pages = 0

        try:
            while pages < settings.GHL_CONTACT_MAX_PAGES:
                page, next_cursor = await self.get_contacts_page(
                    100,
                    (cursor or {}).get("start_after_id"),
                    (cursor or {}).get("start_after"),
                )
                contacts.extend(page)
                pages += 1
                if next_cursor and next_cursor == cursor:
                    raise RuntimeError("GHL returned a repeated contact pagination cursor")
                if not next_cursor:
                    break
                cursor = next_cursor

            return contacts, {
                "status": "connected",
                "pages": pages,
                "max_pages_reached": pages >= settings.GHL_CONTACT_MAX_PAGES and cursor is not None,
            }

        except Exception as exc:
            logger.error(f"Error fetching paginated contacts from GHL: {exc}")
            return contacts, {
                "status": "error",
                "pages": pages,
                "error": "Contact inventory unavailable",
            }

    @staticmethod
    def _contact_matches(
        contact: Dict[str, Any],
        *,
        search: str,
        source: str,
        created_from: Optional[date],
        created_to: Optional[date],
    ) -> bool:
        if source and source not in str(contact.get("source") or "").lower():
            return False
        created_at = str(contact.get("dateAdded") or "")[:10]
        if created_from and (not created_at or created_at < created_from.isoformat()):
            return False
        if created_to and (not created_at or created_at > created_to.isoformat()):
            return False
        if search:
            values = (
                contact.get("name"),
                contact.get("firstName"),
                contact.get("lastName"),
                contact.get("email"),
                contact.get("phone"),
                contact.get("source"),
            )
            if search not in " ".join(str(value or "") for value in values).lower():
                return False
        return True

    async def get_enrollment_lead_page(
        self,
        *,
        limit: int,
        cursor: Optional[Dict[str, str]] = None,
        search: str = "",
        source: str = "",
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
        contact_ids: Optional[set[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch and filter contacts page-by-page without loading the whole GHL location."""
        leads: List[Dict[str, Any]] = []
        seen_identity_keys: set[str] = set()
        next_cursor = cursor
        pages_scanned = 0
        normalized_search = search.strip().lower()
        normalized_source = source.strip().lower()

        while pages_scanned < settings.GHL_CONTACT_PAGE_SCAN_LIMIT:
            requested_cursor = next_cursor
            contacts, next_cursor = await self.get_contacts_page(
                min(limit, 100),
                (next_cursor or {}).get("start_after_id"),
                (next_cursor or {}).get("start_after"),
            )
            pages_scanned += 1
            for raw_contact in contacts:
                contact = self.normalize_contact(raw_contact)
                contact_id = str(contact.get("id") or "")
                if contact_ids is not None and contact_id not in contact_ids:
                    continue
                if contact["identity_key"] in seen_identity_keys:
                    continue
                if not self._contact_matches(
                    contact,
                    search=normalized_search,
                    source=normalized_source,
                    created_from=created_from,
                    created_to=created_to,
                ):
                    continue
                seen_identity_keys.add(contact["identity_key"])
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
                    "firstName": contact.get("firstName"),
                    "lastName": contact.get("lastName"),
                    "name": contact.get("name"),
                    "email": contact.get("email"),
                    "phone": contact.get("phone"),
                    "score": score,
                    "category": category,
                    "source": contact.get("source"),
                    "tags": contact.get("tags", []),
                    "created_at": contact.get("dateAdded"),
                    "updated_at": contact.get("dateUpdated"),
                })
            if next_cursor and next_cursor == requested_cursor:
                raise RuntimeError("GHL returned a repeated contact pagination cursor")
            if leads or not next_cursor or not contacts:
                break

        return {
            "leads": leads,
            "next_cursor": next_cursor,
            "has_more": next_cursor is not None,
            "pages_scanned": pages_scanned,
        }

    async def get_cohort_contact_page(
        self,
        *,
        source: str = "",
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
        limit: int = 500,
        cursor: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Return a bounded cohort page and its continuation cursor for controlled intake."""
        contacts: List[Dict[str, Any]] = []
        next_cursor = cursor
        pages_scanned = 0
        contacts_scanned = 0
        normalized_source = source.strip().lower()
        while pages_scanned < settings.GHL_CONTACT_PAGE_SCAN_LIMIT and len(contacts) < limit:
            requested_cursor = next_cursor
            page, next_cursor = await self.get_contacts_page(
                100,
                (next_cursor or {}).get("start_after_id"),
                (next_cursor or {}).get("start_after"),
            )
            pages_scanned += 1
            contacts_scanned += len(page)
            contacts.extend(
                contact for contact in page
                if self._contact_matches(
                    contact,
                    search="",
                    source=normalized_source,
                    created_from=created_from,
                    created_to=created_to,
                )
            )
            if next_cursor and next_cursor == requested_cursor:
                raise RuntimeError("GHL returned a repeated contact pagination cursor")
            if not next_cursor or not page:
                break
        return {
            "contacts": contacts,
            "next_cursor": next_cursor,
            "has_more": next_cursor is not None,
            "pages_scanned": pages_scanned,
            "contacts_scanned": contacts_scanned,
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

    async def get_contacts_by_ids(
        self,
        contact_ids: list[str],
        *,
        concurrency: int = 5,
    ) -> dict[str, Optional[Dict[str, Any]]]:
        """Fetch exact approved GHL contacts without scanning the whole location."""
        if not self.private_token or not self.location_id:
            raise RuntimeError("GHL_PRIVATE_TOKEN and GHL_LOCATION_ID must be configured to fetch leads")
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")

        semaphore = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient(timeout=30.0) as client:
            async def fetch(contact_id: str) -> tuple[str, Optional[Dict[str, Any]]]:
                async with semaphore:
                    response = await client.get(
                        f"{self.base_url}/contacts/{quote(contact_id, safe='')}",
                        params={"locationId": self.location_id},
                        headers=self.headers,
                    )
                if response.status_code == 404:
                    return contact_id, None
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("GHL returned an invalid contact response")
                contact = payload.get("contact", payload)
                if not isinstance(contact, dict) or str(contact.get("id")) != contact_id:
                    raise ValueError("GHL returned a contact that did not match the requested ID")
                return contact_id, contact

            outcomes = await asyncio.gather(
                *(fetch(contact_id) for contact_id in dict.fromkeys(contact_ids)),
                return_exceptions=True,
            )
        contacts: dict[str, Optional[Dict[str, Any]]] = {}
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                raise outcome
            contact_id, contact = outcome
            contacts[contact_id] = contact
        return contacts

    async def validate_marketing_email_consent(self, contact_id: str, email: str) -> Dict[str, Any]:
        """Verify the recipient address, explicit GHL consent field, and email DND state before a Marketing send."""
        if not settings.GHL_MARKETING_CONSENT_FIELD_ID:
            return {"status": "not_configured", "eligible": False}
        payload = await self.get_contact(contact_id)
        if not payload:
            return {"status": "unavailable", "eligible": False}
        contact = payload.get("contact", payload)
        if not isinstance(contact, dict):
            return {"status": "unavailable", "eligible": False}
        email_matches = str(contact.get("email") or "").strip().lower() == email.strip().lower()
        custom_fields = contact.get("customFields", [])
        if isinstance(custom_fields, dict):
            custom_fields = [custom_fields]
        consent_value = next((field.get("value") for field in custom_fields if isinstance(field, dict) and field.get("id") == settings.GHL_MARKETING_CONSENT_FIELD_ID), None)
        opted_in = consent_value is True or str(consent_value or "").strip().lower() in {"true", "yes", "1", "subscribed", "opted_in", "opted-in"}
        dnd_settings = contact.get("dndSettings") or {}
        email_dnd = bool(contact.get("dnd")) or str((dnd_settings.get("Email") or {}).get("status", "")).lower() in {"active", "enabled"}
        eligible = email_matches and opted_in and not email_dnd
        return {"status": "eligible" if eligible else "ineligible", "eligible": eligible, "email_matches": email_matches, "opted_in": opted_in, "email_dnd": email_dnd}

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

    async def get_contact_opportunity_context(self, contact_id: str) -> Dict[str, Any]:
        """Resolve the contact's opportunity stage from its own pipeline metadata."""
        if not self.private_token or not self.location_id:
            return {"status": "not_configured", "opportunities": [], "pipelines": {}}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/opportunities/search",
                    params={"locationId": self.location_id, "contactId": contact_id, "limit": 100},
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                opportunities = response.json().get("opportunities", [])
                pipelines_response = await client.get(
                    f"{self.base_url}/opportunities/pipelines",
                    params={"locationId": self.location_id},
                    headers=self.headers,
                    timeout=30.0,
                )
                pipelines_response.raise_for_status()
                pipelines = pipelines_response.json().get("pipelines", [])
            pipeline_map = {str(item.get("id")): item for item in pipelines}
            resolved = []
            for opportunity in opportunities:
                pipeline = pipeline_map.get(str(opportunity.get("pipelineId")), {})
                stages = {str(stage.get("id")): stage.get("name") for stage in pipeline.get("stages", [])}
                resolved.append({
                    "id": opportunity.get("id"),
                    "pipeline_id": opportunity.get("pipelineId"),
                    "pipeline_name": pipeline.get("name"),
                    "stage_id": opportunity.get("pipelineStageId"),
                    "stage_name": stages.get(str(opportunity.get("pipelineStageId"))) or opportunity.get("pipelineStageName"),
                    "status": opportunity.get("status"),
                })
            return {"status": "connected", "opportunities": resolved, "pipelines": pipeline_map}
        except Exception as exc:
            logger.error(f"Error resolving GHL opportunity context for {contact_id}: {exc}")
            return {"status": "error", "opportunities": [], "pipelines": {}, "error": "Opportunity context unavailable"}

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
        note: str | None = None,
    ) -> Dict[str, Any]:
        """Write one auditable Enrollment outcome to GHL.

        Score/category tags and queue status are written to the CRM. ENY assignment
        uses Supabase user IDs, so it is recorded locally rather than sent as a
        GHL-native owner ID. Notes use GHL's separate contact notes endpoint.
        """
        tags: list[str] = []
        if category:
            tags.extend(["eny-enrollment", f"eny-score-{category}"])
        if queue_status:
            tags.append(f"eny-status-{queue_status}")

        custom_fields: list[dict[str, Any]] = []
        if score is not None and settings.GHL_SALES_SCORE_FIELD_ID:
            custom_fields.append({"id": settings.GHL_SALES_SCORE_FIELD_ID, "value": score})
        if category and settings.GHL_SCORE_CATEGORY_FIELD_ID:
            custom_fields.append({"id": settings.GHL_SCORE_CATEGORY_FIELD_ID, "value": category})
        if queue_status and settings.GHL_ENROLLMENT_STATUS_FIELD_ID:
            custom_fields.append({"id": settings.GHL_ENROLLMENT_STATUS_FIELD_ID, "value": queue_status})

        payload: Dict[str, Any] = {}
        if custom_fields:
            payload["customFields"] = custom_fields
        if tags:
            contact = await self.get_contact(contact_id)
            if not contact:
                return {
                    "success": False,
                    "contact_updated": False,
                    "note_recorded": False,
                    "error": "Contact not found or unavailable in GHL",
                }
            contact = contact.get("contact", contact)
            if not isinstance(contact, dict):
                return {
                    "success": False,
                    "contact_updated": False,
                    "note_recorded": False,
                    "error": "GHL returned an invalid contact response",
                }
            payload["tags"] = list(dict.fromkeys((contact.get("tags") or []) + tags))
        contact_updated = await self.update_contact(contact_id, payload) if payload else True
        note_recorded = await self.add_contact_note(contact_id, note) if note else True
        return {
            "success": contact_updated and note_recorded,
            "contact_updated": contact_updated,
            "note_recorded": note_recorded,
            "tags": tags,
            "fields_written": [field["id"] for field in custom_fields],
            "assigned_user_id": owner_id,
            "opportunity_context": {"status": "not_requested"},
            "error": None if contact_updated and note_recorded else "GHL write-back incomplete",
        }

    async def get_pipeline_data(self, include_inventory: bool = False) -> Dict[str, Any]:
        """
        Get pipeline/opportunities data from GHL.
        Returns default empty structure if credentials are not configured.
        """
        # Return empty structure if credentials are not configured
        if not self.private_token or not self.location_id:
            logger.warning("GHL credentials not configured - returning empty pipeline data")
            return {
                "status": "not_configured",
                "pipeline_catalog_status": "not_configured",
                "total_leads": 0,
                "conversion_rate": 0.0,
                "revenue_forecast": 0,
                "at_risk_deals": 0,
                "sources_breakdown": {},
                "recent_activities": [],
                "opportunities": [],
                "pipelines": [],
                "max_pages_reached": False,
                "stages": [],
            }

        try:
            opportunity_headers = {**self.headers, "Version": "v3"}
            opportunities: List[Dict[str, Any]] = []
            page = 0
            max_pages = max(1, settings.GHL_OPPORTUNITY_MAX_PAGES) if include_inventory else 1
            max_pages_reached = False
            async with httpx.AsyncClient() as client:
                while page < max_pages:
                    params: Dict[str, Any] = {
                        "locationId": self.location_id,
                        "limit": 100,
                        "status": "all",
                    }
                    if include_inventory:
                        params["page"] = page
                    response = await client.get(
                        f"{self.base_url}/opportunities/search",
                        params=params,
                        headers=opportunity_headers,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    page_opportunities = data.get("opportunities", [])
                    opportunities.extend(page_opportunities)
                    if not include_inventory:
                        break
                    meta = data.get("meta", {}) or {}
                    total_pages = meta.get("totalPages") or meta.get("total_pages")
                    has_more = (
                        page + 1 < int(total_pages)
                        if total_pages is not None
                        else len(page_opportunities) == 100
                    )
                    if not page_opportunities or not has_more:
                        break
                    if page + 1 == max_pages:
                        max_pages_reached = True
                        break
                    page += 1

                if include_inventory:
                    try:
                        pipeline_response = await client.get(
                            f"{self.base_url}/opportunities/pipelines",
                            params={"locationId": self.location_id},
                            headers=self.headers,
                            timeout=30.0,
                        )
                        pipeline_response.raise_for_status()
                        pipeline_payload = pipeline_response.json()
                        pipelines = pipeline_payload.get("pipelines", [])
                        pipeline_catalog_status = "connected"
                    except (httpx.HTTPError, ValueError, TypeError) as exc:
                        logger.error("Error fetching pipeline catalog from GHL: %s", exc)
                        pipelines = []
                        pipeline_catalog_status = "error"
                else:
                    pipelines = []
                    pipeline_catalog_status = "not_requested"

            pipeline_by_id = {
                str(pipeline.get("id")): pipeline
                for pipeline in pipelines
                if pipeline.get("id") is not None
            }
            for opportunity in opportunities:
                pipeline = pipeline_by_id.get(str(opportunity.get("pipelineId")))
                if pipeline:
                    opportunity.setdefault("pipelineName", pipeline.get("name"))
                    stage_by_id = {
                        str(stage.get("id")): stage
                        for stage in pipeline.get("stages", [])
                        if stage.get("id") is not None
                    }
                    stage = stage_by_id.get(str(opportunity.get("pipelineStageId")))
                    if stage:
                        opportunity.setdefault("pipelineStageName", stage.get("name"))

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
                "status": "connected",
                "total_leads": total_leads,
                "conversion_rate": conversion_rate,
                "revenue_forecast": sum(
                    float(opportunity.get("monetaryValue") or opportunity.get("expectedValue") or 0)
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
                "pipelines": pipelines,
                "pipeline_catalog_status": pipeline_catalog_status,
                "max_pages_reached": max_pages_reached,
                "stages": stages,
            }
        except Exception as exc:
            if isinstance(exc, httpx.HTTPStatusError):
                logger.error(
                    "GHL pipeline request failed with HTTP %s: %s",
                    exc.response.status_code,
                    exc.response.text[:1000],
                )
            else:
                logger.error(f"Error fetching pipeline data from GHL: {exc}")
            return {
                "status": "error",
                "total_leads": 0,
                "conversion_rate": 0.0,
                "revenue_forecast": 0,
                "at_risk_deals": 0,
                "sources_breakdown": {},
                "recent_activities": [],
                "opportunities": [],
                "pipelines": [],
                "pipeline_catalog_status": "error",
                "max_pages_reached": False,
                "stages": [],
                "error": "Pipeline data unavailable",
            }

    async def get_ai_context(
        self,
        include_pipeline: bool = True,
        include_contacts: bool = True,
    ) -> Dict[str, Any]:
        """Build only the CRM snapshot permitted for the current AI context."""
        context: Dict[str, Any] = {
            "source": "GoHighLevel",
            "crm_status": "connected" if self.private_token and self.location_id else "not_configured",
        }
        if include_contacts:
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
            context.update({
                "crm_status": inventory_status.get("status", "unknown"),
                "contacts_returned": len(contacts),
                "contact_inventory": inventory_status,
                "scored_contacts": len(scored_leads),
                "unscored_contacts": unscored_contacts,
                "leads_available": bool(scored_leads),
                "scored_leads": scored_leads[:20],
                "score_distribution": score_distribution,
                "contacts_source_breakdown": sources_breakdown,
                "scored_leads_source_breakdown": scored_sources_breakdown,
            })
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

# Create a singleton instance for use in the application
ghl_service = GHLService()
