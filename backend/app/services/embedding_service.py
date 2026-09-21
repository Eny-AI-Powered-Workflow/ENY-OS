# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/embedding_service.py

import httpx
from app.core.config import settings


class EmbeddingService:
    """Create document/query embeddings for semantic SOP retrieval."""

    def __init__(self) -> None:
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.EMBEDDING_MODEL

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def embed(self, text: str) -> list[float]:
        if not self.enabled:
            raise RuntimeError("OPENAI_API_KEY is not configured for knowledge embeddings")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": text},
            )
            response.raise_for_status()
            payload = response.json()
        return payload["data"][0]["embedding"]


embedding_service = EmbeddingService()
