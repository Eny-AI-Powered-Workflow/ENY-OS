"""Regression tests for CORS headers on unhandled exceptions.

The frontend reported ``NetworkError when attempting to fetch resource`` even
though the backend logged a 500. Starlette's ``ServerErrorMiddleware`` sits outside
``CORSMiddleware``, so a raw unhandled exception produced a 500 without an
``Access-Control-Allow-Origin`` header and browsers discarded it.
"""
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from app.core.errors import INTERNAL_ERROR_DETAIL, UnhandledExceptionMiddleware

ALLOWED_ORIGIN = "https://eny-os.vercel.app"


def _build_app(*, include_middleware: bool) -> FastAPI:
    app = FastAPI()
    if include_middleware:
        # Registered first so it sits inside the CORS layer, matching app/main.py.
        app.add_middleware(UnhandledExceptionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Retry-After"],
    )

    @app.get("/crash")
    async def crash():
        raise RuntimeError("simulated unhandled failure")

    @app.get("/healthy")
    async def healthy():
        return {"status": "ok"}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_build_app(include_middleware=True), raise_server_exceptions=False)


def test_unhandled_500_keeps_cors_headers(client):
    response = client.get("/crash", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert response.json() == {"detail": INTERNAL_ERROR_DETAIL}


def test_healthy_response_still_has_cors_headers(client):
    response = client.get("/healthy", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_disallowed_origin_is_not_reflected_on_errors(client):
    response = client.get("/crash", headers={"Origin": "https://attacker.example.com"})

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") is None


def test_without_the_middleware_browser_sees_no_cors_headers():
    """Control case: documents the failure mode this fix removes."""
    bare = TestClient(_build_app(include_middleware=False), raise_server_exceptions=False)

    response = bare.get("/crash", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") is None
