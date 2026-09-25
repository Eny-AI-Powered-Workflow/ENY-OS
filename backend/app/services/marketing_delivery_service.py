# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/marketing_delivery_service.py

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings


class MarketingDeliveryService:
    async def send_ghl_email(
        self,
        recipients: list[dict[str, str]],
        subject: str,
        html: str,
        unsubscribe_url: str,
    ) -> dict[str, Any]:
        """Send approved email through GHL; never send without compliance inputs."""
        if not settings.GHL_PRIVATE_TOKEN or not settings.GHL_MARKETING_FROM_EMAIL:
            return {"status": "not_configured", "sent": 0, "failed": len(recipients), "errors": ["GHL marketing sender is not configured"]}
        sent = 0
        errors: list[str] = []
        async with httpx.AsyncClient() as client:
            for recipient in recipients:
                contact_id = recipient.get("contact_id")
                email = recipient.get("email")
                if not contact_id or not email:
                    errors.append("Recipient is missing contact_id or email")
                    continue
                body = f"{html}\n\n<p><a href=\"{unsubscribe_url}\">Unsubscribe</a></p>"
                try:
                    response = await client.post(
                        f"{settings.GHL_BASE_URL.rstrip('/')}/conversations/messages",
                        params={"locationId": settings.GHL_MARKETING_LOCATION_ID or settings.GHL_LOCATION_ID},
                        headers={
                            "Authorization": f"Bearer {settings.GHL_PRIVATE_TOKEN}",
                            "Version": "2021-04-15",
                            "Content-Type": "application/json",
                        },
                        json={
                            "type": "Email",
                            "contactId": contact_id,
                            "emailTo": email,
                            "emailFrom": settings.GHL_MARKETING_FROM_EMAIL,
                            "subject": subject,
                            "html": body,
                        },
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    sent += 1
                except Exception as exc:
                    errors.append(f"{contact_id}: {exc}")
        return {"status": "sent" if sent and not errors else "partial" if sent else "failed", "sent": sent, "failed": len(recipients) - sent, "errors": errors, "sent_at": datetime.now(timezone.utc).isoformat()}

    async def schedule_buffer(self, text: str, profile_ids: list[str], scheduled_at: datetime) -> dict[str, Any]:
        """Schedule approved social content through Buffer when configured."""
        if not settings.BUFFER_ACCESS_TOKEN or not profile_ids:
            return {"status": "not_configured", "scheduled": 0, "errors": ["Buffer token or profile IDs are not configured"]}
        scheduled = 0
        errors: list[str] = []
        async with httpx.AsyncClient() as client:
            for profile_id in profile_ids:
                try:
                    response = await client.post(
                        "https://api.bufferapp.com/1/updates/create.json",
                        data={
                            "access_token": settings.BUFFER_ACCESS_TOKEN,
                            "profile_ids[]": profile_id,
                            "text": text,
                            "scheduled_at": int(scheduled_at.timestamp()),
                        },
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("success") is False:
                        raise RuntimeError(str(payload))
                    scheduled += 1
                except Exception as exc:
                    errors.append(f"{profile_id}: {exc}")
        return {"status": "scheduled" if scheduled and not errors else "partial" if scheduled else "failed", "scheduled": scheduled, "errors": errors}


marketing_delivery_service = MarketingDeliveryService()
