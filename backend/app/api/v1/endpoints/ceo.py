# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/ceo.py
# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/ceo.py
import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.agent_log import AgentLog
from app.models.role import Role
from app.models.user_role import UserRole
from app.services.supabase_admin_service import supabase_admin_service

router = APIRouter()
logger = logging.getLogger(__name__)


class RoleAssignmentRequest(BaseModel):
    roles: list[str] = Field(default_factory=list, max_length=20)


@router.get("/accounts", dependencies=[Depends(require_permission("users:manage"))])
async def list_accounts(db: Session = Depends(get_db)):
    """List Supabase Auth accounts alongside their database-assigned roles."""
    try:
        auth_users = await supabase_admin_service.list_users()
    except RuntimeError as exc:
        logger.exception("Supabase Auth admin credentials are unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Supabase Auth account directory is not configured",
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Unable to list Supabase Auth accounts")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to load the Supabase Auth account directory",
        ) from exc

    assigned_roles: dict[str, list[str]] = {}
    assignments = (
        db.query(UserRole.user_id, Role.name)
        .join(Role, Role.id == UserRole.role_id)
        .all()
    )
    for user_id, role_name in assignments:
        assigned_roles.setdefault(str(user_id), []).append(role_name)

    assignable_roles = (
        db.query(Role.name)
        .filter(Role.name != "ceo")
        .order_by(Role.name)
        .all()
    )
    accounts = []
    for user in auth_users:
        metadata = user.get("user_metadata") or {}
        accounts.append({
            "id": user.get("id"),
            "email": user.get("email"),
            "full_name": metadata.get("full_name") or metadata.get("name"),
            "created_at": user.get("created_at"),
            "roles": sorted(assigned_roles.get(str(user.get("id")), [])),
        })
    return {
        "accounts": accounts,
        "available_roles": [role_name for (role_name,) in assignable_roles],
    }


@router.put(
    "/accounts/{user_id}/roles",
    dependencies=[Depends(require_permission("users:manage"))],
)
async def assign_account_roles(
    user_id: UUID,
    request: RoleAssignmentRequest,
    db: Session = Depends(get_db),
):
    """Replace an account's non-CEO roles with the CEO-approved role set."""
    role_names = set(request.roles)
    if "ceo" in role_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The CEO role cannot be assigned through account management",
        )

    roles = db.query(Role).filter(Role.name.in_(role_names)).all() if role_names else []
    found_role_names = {role.name for role in roles}
    if found_role_names != role_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more requested roles are not available",
        )

    try:
        db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id.in_(
                db.query(Role.id).filter(Role.name != "ceo")
            ),
        ).delete(synchronize_session=False)
        for role in roles:
            db.add(UserRole(user_id=user_id, role_id=role.id))
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Unable to assign roles to Supabase Auth account %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save role assignments for this account",
        ) from exc

    existing_ceo_role = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id, Role.name == "ceo")
        .first()
    )
    assigned_role_names = sorted(found_role_names)
    if existing_ceo_role:
        assigned_role_names.append("ceo")
    return {"id": str(user_id), "roles": assigned_role_names}


@router.get("/metrics", dependencies=[Depends(require_permission("pipeline:read"))])
async def get_ceo_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get CEO dashboard metrics.
    Requires pipeline:read permission.
    """
    try:
        metrics = {
            "activeUsers": db.query(func.count(func.distinct(UserRole.user_id))).scalar() or 0,
            "aiAgents": db.query(func.count(func.distinct(AgentLog.workflow_name))).scalar() or 0,
            "tasksCompleted": db.query(func.count(AgentLog.id)).filter(AgentLog.status == "success").scalar() or 0,
            "systemUptime": None,
        }
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching CEO metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}",
        )


@router.get("/recent-activity", dependencies=[Depends(require_permission("pipeline:read"))])
async def get_ceo_recent_activity(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get CEO recent activity.
    Requires pipeline:read permission.
    """
    try:
        activities = [
            {
                "id": "1",
                "title": "Monthly Report Generated",
                "description": "Sales team completed Q3 forecast analysis",
                "timeAgo": "2 hours ago",
                "action": "View Report",
                "icon": "activity",
            },
            {
                "id": "2",
                "title": "Agent Task Completed",
                "description": "Enrollment agent processed 150 new applications",
                "timeAgo": "4 hours ago",
                "action": "View Details",
                "icon": "activity",
            },
            {
                "id": "3",
                "title": "System Backup Completed",
                "description": "Daily backup completed successfully",
                "timeAgo": "6 hours ago",
                "action": "View Logs",
                "icon": "activity",
            },
        ]
        return {"activities": activities}
    except Exception as e:
        logger.error(f"Error fetching CEO recent activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recent activity: {str(e)}",
        )


@router.get("/agent-status", dependencies=[Depends(require_permission("pipeline:read"))])
async def get_ceo_agent_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get CEO agent status.
    Requires pipeline:read permission.
    """
    try:
        agents = [
            {
                "id": "1",
                "name": "ENY-SALES-SCORE",
                "type": "workflow",
                "description": "Lead scoring workflow that analyzes and scores leads",
                "status": "success",
                "lastRun": "5 minutes ago",
                "runsToday": 42,
            },
            {
                "id": "2",
                "name": "ENY-MKTG-CONTENT",
                "type": "workflow",
                "description": "Content generation workflow for marketing campaigns",
                "status": "running",
                "lastRun": "2 minutes ago",
                "runsToday": 18,
            },
            {
                "id": "3",
                "name": "ENY-OPS-MONITOR",
                "type": "workflow",
                "description": "System health and performance monitoring",
                "status": "success",
                "lastRun": "1 minute ago",
                "runsToday": 96,
            },
        ]
        return {"agents": agents}
    except Exception as e:
        logger.error(f"Error fetching CEO agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agent status: {str(e)}",
        )