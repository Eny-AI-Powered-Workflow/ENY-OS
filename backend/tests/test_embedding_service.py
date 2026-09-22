"""Regression tests for OpenAI embedding batching, retry and error translation.

Production returned HTTP 500 on ``POST /api/v1/ai/knowledge/ingest`` because the
endpoint issued one embedding request per chunk. A large SOP therefore tripped
OpenAI HTTP 429, which propagated as an unhandled ``httpx.HTTPStatusError``.
"""
import json

import httpx
import pytest

from app.core.config import settings
from app.services.embedding_service import (
    EmbeddingError,
    EmbeddingRateLimitError,
    embedding_service,
)


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _embedding_response(input_count: int, *, reverse: bool = False) -> httpx.Response:
    entries = [
        {"index": index, "embedding": [float(index), 0.0, 1.0]}
        for index in range(input_count)
    ]
    if reverse:
        entries = list(reversed(entries))
    return httpx.Response(200, json={"data": entries, "model": "text-embedding-3-small"})


@pytest.fixture
def configured_service(monkeypatch):
    """Provide an embedding service with an API key and a controllable HTTP client."""
    monkeypatch.setattr(embedding_service, "api_key", "sk-test-key")
    yield embedding_service
    monkeypatch.setattr(embedding_service, "_client", None)


@pytest.mark.asyncio
async def test_chunks_are_batched_into_few_requests(configured_service, monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_BATCH_SIZE", 32)
    batch_sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        inputs = json.loads(request.content)["input"]
        batch_sizes.append(len(inputs))
        return _embedding_response(len(inputs))

    monkeypatch.setattr(configured_service, "_client", _mock_client(handler))
    vectors = await configured_service.embed_many([f"chunk-{index}" for index in range(70)])

    assert batch_sizes == [32, 32, 6], "70 chunks must cost 3 requests, not 70"
    assert len(vectors) == 70


@pytest.mark.asyncio
async def test_embeddings_keep_input_order(configured_service, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        inputs = json.loads(request.content)["input"]
        return _embedding_response(len(inputs), reverse=True)

    monkeypatch.setattr(configured_service, "_client", _mock_client(handler))
    vectors = await configured_service.embed_many(["first", "second", "third"])

    assert [vector[0] for vector in vectors] == [0.0, 1.0, 2.0]


@pytest.mark.asyncio
async def test_rate_limit_is_retried_then_succeeds(configured_service, monkeypatch):
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"error": {"message": "Rate limit reached"}},
            )
        inputs = json.loads(request.content)["input"]
        return _embedding_response(len(inputs))

    monkeypatch.setattr(configured_service, "_client", _mock_client(handler))
    vectors = await configured_service.embed_many(["retry me"])

    assert attempts["count"] == 2
    assert len(vectors) == 1


@pytest.mark.asyncio
async def test_persistent_rate_limit_raises_typed_error(configured_service, monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_MAX_RETRIES", 2)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "0"},
            json={"error": {"message": "Rate limit reached"}},
        )

    monkeypatch.setattr(configured_service, "_client", _mock_client(handler))

    with pytest.raises(EmbeddingRateLimitError):
        await configured_service.embed_many(["always limited"])


@pytest.mark.asyncio
async def test_client_errors_are_not_retried(configured_service, monkeypatch):
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(401, json={"error": {"message": "Invalid API key"}})

    monkeypatch.setattr(configured_service, "_client", _mock_client(handler))

    with pytest.raises(EmbeddingError) as error:
        await configured_service.embed_many(["bad key"])

    assert attempts["count"] == 1, "a 401 must not be retried"
    assert "Invalid API key" in str(error.value)
    assert not isinstance(error.value, EmbeddingRateLimitError)


@pytest.mark.asyncio
async def test_empty_input_makes_no_request(configured_service, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP request should be issued for empty input")

    monkeypatch.setattr(configured_service, "_client", _mock_client(handler))

    assert await configured_service.embed_many([]) == []


@pytest.mark.asyncio
async def test_disabled_service_raises_embedding_error(monkeypatch):
    monkeypatch.setattr(embedding_service, "api_key", "")

    with pytest.raises(EmbeddingError):
        await embedding_service.embed("anything")


def test_embedding_errors_stay_runtime_errors():
    # knowledge_service falls back to full-text search by catching Exception; keeping
    # EmbeddingError a RuntimeError preserves that behaviour for existing callers.
    assert issubclass(EmbeddingError, RuntimeError)
    assert issubclass(EmbeddingRateLimitError, EmbeddingError)
