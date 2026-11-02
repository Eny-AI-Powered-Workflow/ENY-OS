# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.role import Role
from app.models.user_role import UserRole

router = APIRouter()


@router.get("/me")
async def get_current_user_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated user's database-assigned roles.
    """
    roles = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == current_user.id)
        .order_by(Role.name)
        .all()
    )
    return {
        "id": str(current_user.id),
        "roles": [role_name for (role_name,) in roles],
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