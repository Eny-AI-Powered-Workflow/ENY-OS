# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/core/security.py
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.permission import Permission

# Security scheme
security = HTTPBearer()

# Supabase JWT settings
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET
SUPABASE_JWT_AUDIENCE = settings.SUPABASE_JWT_AUDIENCE


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
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
        payload = jwt.decode(
            credentials.credentials,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience=SUPABASE_JWT_AUDIENCE,
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # We don't have a User model in our app, but we can check if the user exists in our user_role table
    # However, note that the user_id from the token is the auth.users.id
    # We can optionally check if the user has any role, but for now we just return the user_id as a string.
    # In a real app, you might want to fetch the user from auth service or have a local user table.
    # For now, we'll return a simple object with the user_id.

    # However, we need to return an object that has an `id` attribute for the require_permission dependency.
    # Let's create a simple class to represent the user.
    class User:
        def __init__(self, id: str):
            self.id = id

    return User(user_id)