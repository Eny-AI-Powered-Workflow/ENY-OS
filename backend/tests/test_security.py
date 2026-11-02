# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_security.py
import base64
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

from app.core import security


def _b64url_integer(value: int) -> str:
    encoded = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(encoded).rstrip(b"=").decode("ascii")


def _new_key_pair() -> tuple[bytes, dict[str, str]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_pem, {
        "kty": "RSA",
        "kid": "test-key",
        "alg": "RS256",
        "use": "sig",
        "n": _b64url_integer(numbers.n),
        "e": _b64url_integer(numbers.e),
    }


PRIVATE_KEY, PUBLIC_JWK = _new_key_pair()
OTHER_PRIVATE_KEY, _ = _new_key_pair()


def _token(
    *,
    issuer: str = security.SUPABASE_ISSUER_BASE,
    audience: str = security.SUPABASE_JWT_AUDIENCE,
    expiry: datetime | None = None,
    signing_key: bytes = PRIVATE_KEY,
    algorithm: str = "RS256",
) -> str:
    payload = {
        "iss": issuer,
        "sub": "user-123",
        "aud": audience,
        "iat": datetime.now(timezone.utc),
        "exp": expiry or (datetime.now(timezone.utc) + timedelta(minutes=5)),
    }
    return jwt.encode(payload, signing_key, algorithm=algorithm, headers={"kid": "test-key"})


@pytest.fixture
def stub_jwks(monkeypatch):
    monkeypatch.setattr(security, "get_jwks", lambda: {"keys": [PUBLIC_JWK]})


def _authenticate(token: str):
    return security.get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )


def test_authenticates_valid_supabase_token(stub_jwks):
    user = _authenticate(_token())

    assert user.id == "user-123"


@pytest.mark.parametrize(
    "token",
    [
        _token(issuer=f"{security.SUPABASE_ISSUER_BASE}/attacker"),
        _token(audience="another-api"),
        _token(expiry=datetime.now(timezone.utc) - timedelta(minutes=1)),
        _token(signing_key=OTHER_PRIVATE_KEY),
        _token(algorithm="HS256", signing_key=b"not-an-rsa-key"),
    ],
    ids=["wrong-issuer", "wrong-audience", "expired", "wrong-signing-key", "unsupported-algorithm"],
)
def test_rejects_invalid_supabase_tokens(token, stub_jwks):
    with pytest.raises(HTTPException) as error:
        _authenticate(token)

    assert error.value.status_code == 401


def test_stale_jwks_is_rejected_after_maximum_age(monkeypatch):
    monkeypatch.setattr(security, "_jwks_cache", {"keys": [PUBLIC_JWK]})
    monkeypatch.setattr(security, "_jwks_cache_time", 100.0)
    monkeypatch.setattr(security, "_stale_jwks_alerted", False)
    monkeypatch.setattr(security, "_last_jwks_failure_log", 0.0)
    monkeypatch.setattr(security.time, "monotonic", lambda: 100.0 + security.MAX_STALE_JWKS_SECONDS + 1)
    monkeypatch.setattr(
        security.requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.ConnectionError("unavailable")),
    )

    with pytest.raises(RuntimeError, match="maximum stale age"):
        security.get_jwks()
