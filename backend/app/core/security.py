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
from sqlalchemy import text
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.permission import Permission

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

logger = logging.getLogger(__name__)

def get_jwks():
    """Fetch and cache the JWKS from Supabase using the anon key."""
    global _jwks_cache, _jwks_cache_time
    now = time.time()
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

def sync_user_roles_from_token(db: Session, user_id: str, token_payload: dict):
    """
    Sync the user's roles from the token payload to the user_roles table.
    This ensures that the user has the correct roles in our database based on their Supabase token.
    """
    try:
        # Extract roles from the token payload
        user_metadata = token_payload.get('user_metadata', {})
        token_roles = user_metadata.get('roles', [])
        if not token_roles:
            # If no roles in token, we can't sync
            logger.warning(f"No roles found in token for user {user_id}")
            return

        # Get the role IDs for the roles in the token
        role_names = [role.strip().lower() for role in token_roles if role.strip()]
        if not role_names:
            return

        # Query existing roles from the database
        stmt = text("SELECT id, name FROM roles WHERE LOWER(name) IN :role_names")
        result = db.execute(stmt, {"role_names": tuple(role_names)})
        db_roles = {row[1].lower(): row[0] for row in result.fetchall()}

        # For each role in the token, ensure the user has it in user_roles
        for role_name in role_names:
            role_id = db_roles.get(role_name.lower())
            if not role_id:
                logger.warning(f"Role '{role_name}' not found in database for user {user_id}")
                continue

            # Check if the user already has this role
            stmt = text("""
                SELECT 1 FROM user_roles
                WHERE user_id = :user_id AND role_id = :role_id
            """)
            result = db.execute(stmt, {"user_id": user_id, "role_id": role_id})
            if result.fetchone():
                # User already has this role, nothing to do
                continue

            # Insert the user role
            stmt = text("""
                INSERT INTO user_roles (user_id, role_id, created_at, updated_at)
                VALUES (:user_id, :role_id, NOW(), NOW())
            """)
            db.execute(stmt, {"user_id": user_id, "role_id": role_id})
            logger.info(f"Assigned role '{role_name}' to user {user_id}")

        # Commit the changes
        db.commit()
    except Exception as e:
        logger.error(f"Error syncing user roles for {user_id}: {e}")
        db.rollback()
        # Don't raise the exception because we don't want to fail the authentication
        # if role syncing fails. The user might still have the required permissions
        # from previous logins.

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

        # Get unverified payload to check the issuer
        unverified_payload = jwt.get_unverified_claims(token)
        issuer = unverified_payload.get('iss')
        if issuer is None:
            logger.error("JWT payload missing 'iss' claim")
            raise credentials_exception
        # Check that the issuer starts with the expected base issuer
        if not issuer.startswith(SUPABASE_ISSUER_BASE):
            logger.error(f"JWT issuer '{issuer}' does not start with expected base issuer '{SUPABASE_ISSUER_BASE}'")
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

        # Verify the token with the issuer from the token (which we know starts with the base)
        payload = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=SUPABASE_JWT_AUDIENCE,
            issuer=issuer,  # Use the issuer from the token (after prefix check)
        )
        logger.info(f"Token payload: {payload}")

        user_id: str = payload.get("sub")
        if user_id is None:
            logger.error("JWT payload missing 'sub' claim")
            raise credentials_exception

        logger.info(f"Successfully authenticated user_id: {user_id}")

        # Sync the user's roles from the token to our database
        sync_user_roles_from_token(db, user_id, payload)

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