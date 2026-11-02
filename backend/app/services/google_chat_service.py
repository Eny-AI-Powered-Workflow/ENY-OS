# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/google_chat_service.py
from typing import Any

import httpx

from app.core.config import settings


class GoogleChatService:
    """Send backend-generated notifications to the configured Google Chat space."""

    async def send_message(self, text: str) -> dict[str, Any]:
        webhook_url = settings.GOOGLE_CHAT_SALES_WEBHOOK_URL.strip()
        if not webhook_url:
            return {"status": "not_configured"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json={"text": text})
            response.raise_for_status()

        return {"status": "sent"}


google_chat_service = GoogleChatService()
