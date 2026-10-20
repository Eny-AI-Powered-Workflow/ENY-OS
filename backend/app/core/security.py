# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/core/security.py
import logging
import time
from threading import Lock

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk
from jose.exceptions import JOSEError
import requests
from app.core.config import settings

# Security scheme
security = HTTPBearer()

# Supabase JWT settings
SUPABASE_JWT_AUDIENCE = settings.SUPABASE_JWT_AUDIENCE
SUPABASE_URL = settings.SUPABASE_URL.rstrip('/')  # Remove trailing slash if any
# Derive issuer and JWKS URL from Supabase URL
SUPABASE_ISSUER_BASE = f"{SUPABASE_URL}/auth/v1"
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY  # For accessing JWKS endpoint

# Cache for JWKS to avoid fetching on every request
_jwks_cache = None
_jwks_cache_time = 0
CACHE_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_STALE_JWKS_SECONDS = 3600
JWKS_FAILURE_LOG_INTERVAL_SECONDS = 300
ALLOWED_JWT_ALGORITHMS = {"ES256", "RS256"}
_stale_jwks_alerted = False
_last_jwks_failure_log = 0.0
_jwks_refresh_lock = Lock()

logger = logging.getLogger(__name__)


def get_jwks():
    """Fetch and cache the JWKS from Supabase using the anon key."""
    global _jwks_cache, _jwks_cache_time, _stale_jwks_alerted, _last_jwks_failure_log
    now = time.monotonic()
    if _jwks_cache is not None and (now - _jwks_cache_time) < CACHE_TIMEOUT_SECONDS:
        return _jwks_cache
    with _jwks_refresh_lock:
        now = time.monotonic()
        if _jwks_cache is not None and (now - _jwks_cache_time) < CACHE_TIMEOUT_SECONDS:
            return _jwks_cache
        try:
            headers = {
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            }
            response = requests.get(SUPABASE_JWKS_URL, headers=headers, timeout=10)
            response.raise_for_status()
            jwks = response.json()
            if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
                raise ValueError("Supabase returned an invalid JWKS document")
            _jwks_cache = jwks
            _jwks_cache_time = time.monotonic()
            _stale_jwks_alerted = False
            return jwks
        except (requests.RequestException, ValueError) as exc:
            age = now - _jwks_cache_time if _jwks_cache is not None else None
            if now - _last_jwks_failure_log >= JWKS_FAILURE_LOG_INTERVAL_SECONDS:
                logger.error("Failed to refresh Supabase JWKS: %s", exc)
                _last_jwks_failure_log = now
            if _jwks_cache is not None and age is not None and age <= MAX_STALE_JWKS_SECONDS:
                if not _stale_jwks_alerted:
                    logger.warning("Using stale Supabase JWKS; cache age is %.0f seconds", age)
                    _stale_jwks_alerted = True
                return _jwks_cache
            raise RuntimeError("Supabase JWKS unavailable or cache exceeded maximum stale age") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Validate the JWT token and return the user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        # Get the unverified header to extract the key ID (kid) and algorithm
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
        algorithm = header.get('alg')

        if not isinstance(kid, str) or algorithm not in ALLOWED_JWT_ALGORITHMS:
            raise credentials_exception

        # Reject tokens for another issuer before consulting the JWKS endpoint.
        unverified_payload = jwt.get_unverified_claims(token)
        issuer = unverified_payload.get('iss')
        if issuer != SUPABASE_ISSUER_BASE:
            raise credentials_exception

        # Fetch JWKS and find the matching key
        jwks = get_jwks()
        key_dict = None
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                key_dict = key
                break

        if key_dict is None:
            raise credentials_exception
        if key_dict.get("alg") not in (None, algorithm):
            raise credentials_exception

        # Construct the public key from the JWK
        key = jwk.construct(key_dict, algorithm=algorithm)

        # Validate the signature and claims against the configured issuer and audience.
        payload = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=SUPABASE_JWT_AUDIENCE,
            issuer=SUPABASE_ISSUER_BASE,
        )
        user_id: str = payload.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise credentials_exception

    except JOSEError:
        raise credentials_exception
    except (RuntimeError, requests.RequestException, ValueError):
        raise credentials_exception

    metadata = payload.get("user_metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    display_name = (
        metadata.get("full_name")
        or metadata.get("name")
        or metadata.get("display_name")
        or "there"
    )
    if not isinstance(display_name, str):
        display_name = "there"
    display_name = " ".join(display_name.split())[:120] or "there"

    class User:
        def __init__(self, id: str, display_name: str):
            self.id = id
            self.display_name = display_name

    return User(user_id, display_name)