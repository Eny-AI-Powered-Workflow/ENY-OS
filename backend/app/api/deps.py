# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/deps.py
import logging
from typing import Any, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole

logger = logging.getLogger(__name__)


def require_permission(permission_scope: str):
    """
    Dependency factory that creates a permission checker for the given scope.

    This is the SINGLE enforcement point for all permissions in the system.
    Every protected route must use this dependency.

    Args:
        permission_scope: The permission scope to check (e.g., "leads:read")

    Returns:
        A dependency function that checks the permission and logs the attempt
    """
    def permission_checker(
        current_user: Annotated[Any, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)]
    ):
        # Check if user has the required permission through their roles
        user_has_permission = (
            db.query(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .join(UserRole, RolePermission.role_id == UserRole.role_id)
            .filter(UserRole.user_id == current_user.id)
            .filter(Permission.scope == permission_scope)
            .first()
        ) is not None

        # Create audit log entry for this permission check (pass or fail)
        audit_log = AuditLog(
            user_id=current_user.id,
            permission_scope=permission_scope,
            granted=user_has_permission,
            path="",  # TODO: Get actual path from request
        )
        db.add(audit_log)
        db.commit()

        # Log the permission check for debugging
        logger.info(f"Permission check: user_id={current_user.id}, scope='{permission_scope}', granted={user_has_permission}")

        # If permission not granted, raise 403
        if not user_has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_scope}",
            )

        # If granted, return the user for use in the route handler
        return current_user

    return permission_checker