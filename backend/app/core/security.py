# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/core/security.py
import logging
import time
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
import requests
from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.permission import Permission

# Security scheme
security = HTTPBearer()

# Supabase JWT settings
SUPABASE_JWT_AUDIENCE = settings.SUPABASE_JWT_AUDIENCE
SUPABASE_URL = settings.SUPABASE_URL.rstrip('/')  # Remove trailing slash if any
# Derive issuer and JWKS URL from Supabase URL
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/keys"

# Cache for JWKS to avoid fetching on every request
_jwks_cache = None
_jwks_cache_time = 0
CACHE_TIMEOUT_SECONDS = 300  # 5 minutes

logger = logging.getLogger(__name__)

def get_jwks():
    """Fetch and cache the JWKS from Supabase."""
    global _jwks_cache, _jwks_cache_time
    now = time.time()
    if _jwks_cache is not None and (now - _jwks_cache_time) < CACHE_TIMEOUT_SECONDS:
        return _jwks_cache
    try:
        response = requests.get(SUPABASE_JWKS_URL, timeout=10)
        response.raise_for_status()
        jwks = response.json()
        _jwks_cache = jwks
        _jwks_cache_time = now
        return jwks
    except Exception as e:
        logger.error(f"Failed to fetch JWKS from {SUPABASE_JWKS_URL}: {e}")
        # Return cached JWKS if available, otherwise raise
        if _jwks_cache is not None:
            logger.warning("Using stale JWKS cache due to fetch failure")
            return _jwks_cache
        raise

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Validate the JWT token and return the user.
    """
    logger.info(f"get_current_user called with token: {credentials.credentials[:50]}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        logger.info(f"Token received: {token[:50]}...")
        # Get the unverified header to extract the key ID (kid) and algorithm
        header = jwt.get_unverified_header(token)
        logger.info(f"Token header: {header}")
        kid = header.get('kid')
        algorithm = header.get('alg')

        if kid is None or algorithm is None:
            logger.error("JWT header missing 'kid' or 'alg'")
            raise credentials_exception

        # Fetch JWKS and find the matching key
        logger.info(f"Fetching JWKS from: {SUPABASE_JWKS_URL}")
        jwks = get_jwks()
        logger.info(f"JWKS received: {jwks}")
        key_dict = None
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                key_dict = key
                break

        if key_dict is None:
            logger.error(f"No matching key found for kid: {kid}")
            raise credentials_exception

        # Construct the public key from the JWK
        key = jwk.construct(key_dict, algorithm=algorithm)
        logger.info(f"Constructed key: {key}")

        # Verify the token
        payload = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=SUPABASE_JWT_AUDIENCE,
            issuer=SUPABASE_ISSUER,
        )
        logger.info(f"Token payload: {payload}")

        user_id: str = payload.get("sub")
        if user_id is None:
            logger.error("JWT payload missing 'sub' claim")
            raise credentials_exception

        logger.info(f"Successfully authenticated user_id: {user_id}")

    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error during JWT validation: {e}")
        raise credentials_exception

    # Return a simple user object with an id attribute
    class User:
        def __init__(self, id: str):
            self.id = id

    return User(user_id)