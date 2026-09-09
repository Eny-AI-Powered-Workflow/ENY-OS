# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/ai.py

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.role import Role
from app.models.user_role import UserRole
from app.services.claude_service import ClaudeService

router = APIRouter()

ROLE_CONTEXTS = {
    "ceo": "executive leadership, company strategy, revenue, and decision support",
    "programs_manager": "program delivery, operations, and student experience",
    "customer_success": "customer success, retention, student health, and support",
    "business_support": "business support, marketing coordination, and administration",
    "executive_assistant": "executive assistance, opportunity research, and prioritization",
    "enrollment": "sales, enrollment, lead qualification, and follow-up",
    "developer": "platform engineering, automation, integrations, and technical delivery",
}


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)


def get_user_roles(current_user: Any, db: Session) -> list[str]:
    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == current_user.id)
        .all()
    )
    return [row[0] for row in rows]


@router.post(
    "/chat",
    dependencies=[Depends(require_permission("ai:chat"))],
)
async def chat_with_department_ai(
    request: ChatRequest,
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a Claude response constrained by the authenticated user's roles."""
    roles = get_user_roles(current_user, db)
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No department role is assigned to this user",
        )

    contexts = [ROLE_CONTEXTS.get(role, role.replace("_", " ")) for role in roles]
    role_context = "; ".join(contexts)

    try:
        answer = await ClaudeService().invoke(
            prompt=request.prompt,
            role_context=role_context,
            max_tokens=1200,
            temperature=0.4,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service is unavailable: {exc}",
        ) from exc

    return {
        "answer": answer,
        "roles": roles,
        "department_context": role_context,
    }