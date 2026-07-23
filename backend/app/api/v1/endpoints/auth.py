# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user

router = APIRouter()


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user information.
    This endpoint validates the JWT token and returns user info.
    """
    return {
        "id": current_user.get("id"),
        "email": current_user.get("email"),
        "role": current_user.get("role", "user"),
        "is_active": True
    }


@router.post("/refresh")
async def refresh_token():
    """
    Refresh authentication token.
    In a real implementation with Supabase, this would be handled by the frontend
    using Supabase's refresh token mechanism.
    """
    return {
        "message": "Token refresh should be handled by Supabase client on frontend",
        "status": "success"
    }


@router.get("/status")
async def auth_status():
    """
    Check authentication service status.
    """
    return {
        "status": "authenticated",
        "provider": "supabase",
        "message": "Authentication service is operational"
    }