# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/webflow_service.py

from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.core.config import settings


class WebflowService:
    base_url = "https://api.webflow.com/v2"

    def configuration_status(self) -> dict[str, Any]:
        return {
            "configured": bool(settings.WEBFLOW_ACCESS_TOKEN and settings.WEBFLOW_SITE_ID and settings.WEBFLOW_CMS_COLLECTION_ID),
            "provider": "webflow",
            "site_configured": bool(settings.WEBFLOW_SITE_ID),
            "collection_configured": bool(settings.WEBFLOW_CMS_COLLECTION_ID),
            "subdomain_publish_enabled": settings.WEBFLOW_PUBLISH_TO_SUBDOMAIN,
        }

    def _collection_id(self, funnel: Any) -> str:
        collection_id = funnel.collection_id or settings.WEBFLOW_CMS_COLLECTION_ID
        if not settings.WEBFLOW_ACCESS_TOKEN or not collection_id:
            raise HTTPException(status_code=503, detail="Set WEBFLOW_ACCESS_TOKEN and WEBFLOW_CMS_COLLECTION_ID in the backend environment")
        return collection_id

    async def stage_variant(self, funnel: Any, variant: Any) -> dict[str, Any]:
        collection_id = quote(self._collection_id(funnel), safe="")
        field_data = dict(variant.content_json or {})
        if not isinstance(field_data.get("name"), str) or not field_data["name"].strip():
            raise HTTPException(status_code=422, detail="Webflow CMS fieldData requires a non-empty name")
        if not isinstance(field_data.get("slug"), str) or not field_data["slug"].strip():
            raise HTTPException(status_code=422, detail="Webflow CMS fieldData requires a non-empty slug")
        payload: dict[str, Any]
        if variant.external_item_id:
            payload = {"items": [{"id": variant.external_item_id, "isDraft": True, "fieldData": field_data}]}
            method = "PATCH"
            path = f"/collections/{collection_id}/items"
        else:
            payload = {"items": [{"isDraft": True, "fieldData": field_data}]}
            method = "POST"
            path = f"/collections/{collection_id}/items/insert"
        result = await self._request(method, path, payload)
        items = result.get("items") or []
        if not items or not items[0].get("id"):
            raise HTTPException(status_code=502, detail="Webflow did not return a staged CMS item ID")
        return {"item_id": str(items[0]["id"]), "status": "staged", "provider_response": result}

    async def publish_variant(self, funnel: Any, item_id: str) -> dict[str, Any]:
        collection_id = quote(self._collection_id(funnel), safe="")
        result = await self._request("POST", f"/collections/{collection_id}/items/publish", {"itemIds": [item_id]})
        published_ids = result.get("publishedItemIds") or []
        errors = result.get("errors") or []
        if item_id not in published_ids or errors:
            raise HTTPException(status_code=502, detail={"message": "Webflow did not confirm item publication", "errors": errors})
        return {"status": "published", "published_item_id": item_id, "provider_response": result}

    async def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not settings.WEBFLOW_ACCESS_TOKEN:
            raise HTTPException(status_code=503, detail="WEBFLOW_ACCESS_TOKEN is not configured")
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={"Authorization": f"Bearer {settings.WEBFLOW_ACCESS_TOKEN}", "Content-Type": "application/json"},
                    json=body,
                )
                response.raise_for_status()
                return response.json() if response.content else {}
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 429:
                raise HTTPException(status_code=429, detail="Webflow rate limit reached; retry after the provider reset") from exc
            if status_code in {401, 403}:
                raise HTTPException(status_code=403, detail="Webflow credentials or CMS write scope are not authorized") from exc
            if status_code == 404:
                raise HTTPException(status_code=404, detail="Webflow site, CMS collection, or item was not found") from exc
            raise HTTPException(status_code=502, detail="Webflow rejected the staged CMS update") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Webflow is currently unavailable") from exc


webflow_service = WebflowService()
