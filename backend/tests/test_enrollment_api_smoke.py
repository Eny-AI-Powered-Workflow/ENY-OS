# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_enrollment_api_smoke.py
"""Optional authenticated smoke test for a running local backend."""
import os

import httpx
import pytest


API_URL = os.getenv("ENY_API_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.getenv("ENY_SMOKE_TOKEN")


@pytest.mark.asyncio
@pytest.mark.skipif(not TOKEN, reason="Set ENY_SMOKE_TOKEN to run the authenticated smoke test")
async def test_authenticated_enrollment_smoke():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(base_url=API_URL, headers=headers, timeout=20) as client:
        for path in ("/api/v1/enrollment/metrics", "/api/v1/enrollment/pipeline", "/api/v1/enrollment/batch-results"):
            response = await client.get(path)
            assert response.status_code == 200, f"{path}: {response.status_code} {response.text}"
            assert isinstance(response.json(), dict)
