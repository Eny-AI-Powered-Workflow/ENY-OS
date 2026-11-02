# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_request_guard.py
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.types import Message, Scope

from app.core.request_guard import RequestGuardMiddleware


@pytest.mark.asyncio
async def test_rejects_streamed_body_over_limit():
    async def app(scope: Scope, receive, send) -> None:
        await receive()
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = RequestGuardMiddleware(
        app,
        max_body_bytes=4,
        max_concurrent_requests=1,
        production=True,
    )
    incoming: list[Message] = [
        {"type": "http.request", "body": b"123", "more_body": True},
        {"type": "http.request", "body": b"45", "more_body": False},
    ]
    sent: list[Message] = []

    async def receive() -> Message:
        return incoming.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "headers": [],
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
    }

    await middleware(scope, receive, send)

    assert sent[0]["status"] == 413
    assert b"x-content-type-options" in dict(sent[0]["headers"])


@pytest.mark.asyncio
async def test_rejects_declared_oversized_body_before_reading_it():
    async def app(scope, receive, send) -> None:
        pytest.fail("oversized body should be rejected before route execution")

    middleware = RequestGuardMiddleware(
        app,
        max_body_bytes=4,
        max_concurrent_requests=1,
        production=False,
    )
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "headers": [(b"content-length", b"5")],
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
    }

    await middleware(scope, receive, send)

    assert sent[0]["status"] == 413


def test_edge_secret_blocks_direct_access_but_preserves_health_checks():
    app = FastAPI()
    app.add_middleware(
        RequestGuardMiddleware,
        max_body_bytes=1024,
        max_concurrent_requests=1,
        production=True,
        edge_shared_secret="test-edge-secret",
    )

    @app.get("/resource")
    async def resource():
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    with TestClient(app) as client:
        assert client.get("/resource").status_code == 403
        assert client.get(
            "/resource",
            headers={"X-ENY-Edge-Token": "test-edge-secret"},
        ).status_code == 200
        assert client.get("/health").status_code == 200


@pytest.mark.asyncio
async def test_returns_retryable_status_when_process_capacity_is_exhausted():
    async def app(scope: Scope, receive, send) -> None:
        if scope["path"] != "/health":
            pytest.fail("request should be rejected when no slots are available")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = RequestGuardMiddleware(
        app,
        max_body_bytes=1024,
        max_concurrent_requests=1,
        production=False,
    )
    assert middleware.request_slots.acquire(blocking=False)
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/resource",
        "raw_path": b"/resource",
        "query_string": b"",
        "headers": [],
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
    }

    try:
        await middleware(scope, receive, send)
        scope["path"] = "/health"
        scope["raw_path"] = b"/health"
        await middleware(scope, receive, send)
    finally:
        middleware.request_slots.release()

    assert sent[0]["status"] == 503
    assert dict(sent[0]["headers"])[b"retry-after"] == b"1"
    assert sent[2]["status"] == 200
