import asyncio
import logging
import random
from typing import Optional, Sequence

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
RETRYABLE_HTTP_STATUSES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


class EmbeddingError(RuntimeError):
    """Raised when an embedding request cannot be completed."""


class EmbeddingRateLimitError(EmbeddingError):
    """Raised when OpenAI keeps returning HTTP 429 after every retry."""


class EmbeddingService:
    """Create document/query embeddings for semantic SOP retrieval.

    OpenAI bills and rate limits per request, so chunks are submitted in batches
    and retried with exponential backoff. A large SOP therefore costs a handful of
    requests instead of one request per chunk, which is what pushed ingestion into
    HTTP 429 in production.
    """

    def __init__(self) -> None:
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=settings.EMBEDDING_TIMEOUT_SECONDS)
        return self._client

    async def aclose(self) -> None:
        """Release the pooled HTTP client (used by tests and shutdown hooks)."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def embed(self, text: str) -> list[float]:
        """Embed a single string."""
        vectors = await self.embed_many([text])
        return vectors[0]

    async def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed many strings, returning vectors in the same order as the input."""
        if not self.enabled:
            raise EmbeddingError("OPENAI_API_KEY is not configured for knowledge embeddings")
        if not texts:
            return []

        normalized = [text if text and text.strip() else " " for text in texts]
        batch_size = max(1, settings.EMBEDDING_BATCH_SIZE)
        vectors: list[list[float]] = []
        for start in range(0, len(normalized), batch_size):
            batch = normalized[start:start + batch_size]
            vectors.extend(await self._embed_batch(batch))

        if len(vectors) != len(normalized):
            raise EmbeddingError(
                f"OpenAI returned {len(vectors)} embeddings for {len(normalized)} inputs"
            )
        return vectors

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        response = await self._post_with_retry(batch)
        try:
            payload = response.json()
            entries = payload["data"]
        except (ValueError, KeyError, TypeError) as exc:
            raise EmbeddingError("OpenAI returned an unexpected embeddings response") from exc

        ordered = sorted(entries, key=lambda entry: entry.get("index", 0))
        try:
            return [entry["embedding"] for entry in ordered]
        except (KeyError, TypeError) as exc:
            raise EmbeddingError("OpenAI embeddings response was missing vector data") from exc

    async def _post_with_retry(self, batch: list[str]) -> httpx.Response:
        client = self._get_client()
        max_retries = max(0, settings.EMBEDDING_MAX_RETRIES)
        last_error: Optional[httpx.HTTPStatusError | httpx.TransportError] = None

        for attempt in range(max_retries + 1):
            try:
                response = await client.post(
                    OPENAI_EMBEDDINGS_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": batch},
                )
            except httpx.TransportError as exc:
                last_error = exc
                if attempt == max_retries:
                    break
                await self._sleep_before_retry(attempt, None, exc)
                continue

            if response.status_code < 400:
                return response

            last_error = httpx.HTTPStatusError(
                f"OpenAI embeddings request failed with status {response.status_code}",
                request=response.request,
                response=response,
            )
            if response.status_code not in RETRYABLE_HTTP_STATUSES or attempt == max_retries:
                break

            await self._sleep_before_retry(attempt, response, last_error)

        raise self._translate_error(last_error)

    async def _sleep_before_retry(
        self,
        attempt: int,
        response: Optional[httpx.Response],
        reason: Exception,
    ) -> None:
        delay = self._retry_delay(attempt, response)
        logger.warning(
            "OpenAI embeddings retry %s/%s in %.2fs after %s",
            attempt + 1,
            max(0, settings.EMBEDDING_MAX_RETRIES),
            delay,
            reason,
        )
        await asyncio.sleep(delay)

    @staticmethod
    def _retry_delay(attempt: int, response: Optional[httpx.Response]) -> float:
        """Honour Retry-After when OpenAI sends it, otherwise back off exponentially."""
        requested_delay: Optional[float] = None
        if response is not None:
            header = response.headers.get("retry-after")
            if header:
                try:
                    requested_delay = float(header)
                except ValueError:
                    requested_delay = None

        if requested_delay is None:
            base = max(0.1, settings.EMBEDDING_RETRY_BASE_SECONDS)
            requested_delay = base * (2 ** attempt)

        ceiling = max(0.1, settings.EMBEDDING_RETRY_MAX_SECONDS)
        return min(requested_delay, ceiling) + random.uniform(0, 0.25)

    @staticmethod
    def _translate_error(
        error: Optional[httpx.HTTPStatusError | httpx.TransportError],
    ) -> EmbeddingError:
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code == 429:
                return EmbeddingRateLimitError(
                    "OpenAI rate limit reached while embedding the knowledge document"
                )
            detail = ""
            try:
                detail = str(error.response.json().get("error", {}).get("message", ""))
            except (ValueError, AttributeError):
                detail = ""
            message = f"OpenAI embeddings request failed with status {status_code}"
            return EmbeddingError(f"{message}: {detail}" if detail else message)
        if error is not None:
            return EmbeddingError(f"OpenAI embeddings request failed: {error}")
        return EmbeddingError("OpenAI embeddings request failed")


embedding_service = EmbeddingService()
