# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/supabase_admin_service.py
from typing import Any

import httpx

from app.core.config import settings


class SupabaseAdminService:
    """Use the Supabase Auth admin API for account-directory administration."""

    async def list_users(self) -> list[dict[str, Any]]:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError("Supabase Auth admin credentials are not configured")

        users: list[dict[str, Any]] = []
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            for page in range(1, 101):
                response = await client.get(
                    f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users",
                    params={"page": page, "per_page": 100},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
                page_users = payload.get("users") if isinstance(payload, dict) else None
                if not isinstance(page_users, list):
                    raise RuntimeError("Supabase Auth returned an invalid user directory response")
                users.extend(user for user in page_users if isinstance(user, dict))
                if len(page_users) < 100:
                    return users

        raise RuntimeError("Supabase Auth user directory exceeded the supported pagination limit")


supabase_admin_service = SupabaseAdminService()
