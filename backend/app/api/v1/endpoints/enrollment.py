# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/enrollment.py
from datetime import datetime, timedelta, timezone
import hmac
import httpx
import anthropic
from fastapi import APIRouter, Depends, Header, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Any, Optional, Literal
from app.api.deps import get_optional_permissions_with_audit, require_permission
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from sqlalchemy import and_, func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
import logging
from uuid import UUID
from types import SimpleNamespace

from app.models.batch_execution_result import BatchExecutionResult
from app.models.batch_retry import BatchRetry
from app.models.cohort_approval import CohortApproval
from app.models.enrollment_audit import EnrollmentAudit
from app.models.lead_assignment import LeadAssignment
from app.models.operational_alert import OperationalAlert
from app.models.operational_alert_user_state import OperationalAlertUserState
from app.models.ghl_lead_intake import GHLLeadIntake
from app.services.batch_execution_service import retry_batch_result
from app.services.claude_service import ClaudeService
from app.services.ghl_service import ghl_service
from app.services.google_chat_service import google_chat_service
from app.models.role import Role
from app.models.user_role import UserRole
from app.services.supabase_admin_service import supabase_admin_service

router = APIRouter()
logger = logging.getLogger(__name__)
QUEUE_STATES = {"new", "assigned", "contacted", "qualified", "closed"}
QUEUE_TRANSITIONS = {
    "new": {"assigned"},
    "assigned": {"contacted"},
    "contacted": {"qualified", "closed"},
    "qualified": {"closed"},
    "closed": set(),
}
SLA_RULES = {
    "new_owner_minutes": 15,
    "assigned_contact_minutes": 60,
    "contacted_follow_up_hours": 24,
    "workflow_retry_minutes": 30,
    "data_quality_hours": 24,
}
OPERATING_POLICY = {
    "ownership": [
        "Every hot lead is claimed before outreach.",
        "The assigned owner remains accountable until closed, enrolled, or escalated.",
        "Unassigned hot leads are reviewed within 15 minutes.",
    ],
    "follow_up": [
        "Run the approved follow-up workflow only from an assigned lead.",
        "Record response, next step, booking, and outcome in the lifecycle.",
        "Do not skip lifecycle stages without an auditable reason.",
    ],
    "escalation": [
        "Escalate stale work, failed write-back, and exhausted retries.",
        "A recovery decision is required before rerun.",
    ],
    "weekly_review": [
        "Review intake, no-contact aging, source conversion, owner workload, and closed outcomes.",
        "Assign an owner and due date to every open alert.",
    ],
}
LIFECYCLE_STAGES = {
    "not_started",
    "queued",
    "outreach_sent",
    "responded",
    "next_step",
    "booked",
    "enrolled",
    "lost",
    "failed",
}
LIFECYCLE_TRANSITIONS = {
    "not_started": {"queued", "failed"},
    "queued": {"outreach_sent", "responded", "failed"},
    "outreach_sent": {"responded", "failed"},
    "responded": {"next_step", "booked", "lost"},
    "next_step": {"booked", "lost"},
    "booked": {"enrolled", "lost"},
    "enrolled": set(),
    "lost": set(),
    "failed": {"queued", "lost"},
}


class QueueStateRequest(BaseModel):
    state: str = Field(..., min_length=1, max_length=30)
    reason: str = Field(..., min_length=3, max_length=500)


class LeadAssignmentRequest(BaseModel):
    assigned_user_id: UUID
    department: Optional[Literal["sales", "enrollment"]] = None


ASSIGNMENT_PERMISSION_SCOPES = {
    "sales": "sales:leads:assign",
    "enrollment": "enrollment:leads:assign",
}


def _assignment_departments(db: Session, user_id: Any, path: str) -> set[str]:
    scopes = get_optional_permissions_with_audit(
        SimpleNamespace(id=user_id),
        db,
        tuple(ASSIGNMENT_PERMISSION_SCOPES.values()),
        path,
    )
    return {
        department
        for department, scope in ASSIGNMENT_PERMISSION_SCOPES.items()
        if scope in scopes
    }


def _record_lead_assignment(
    db: Session,
    *,
    contact_id: str,
    assigned_user_id: UUID,
    assigned_department: str,
    assigned_by_user_id: Any,
) -> UUID | None:
    assignment = db.query(LeadAssignment).filter(LeadAssignment.contact_id == contact_id).first()
    previous_owner_id = assignment.assigned_user_id if assignment else None
    if assignment:
        assignment.assigned_user_id = assigned_user_id
        assignment.assigned_department = assigned_department
        assignment.assigned_by_user_id = assigned_by_user_id
    else:
        db.add(LeadAssignment(
            contact_id=contact_id,
            assigned_user_id=assigned_user_id,
            assigned_department=assigned_department,
            assigned_by_user_id=assigned_by_user_id,
        ))
    return previous_owner_id


class BatchDecisionRequest(BaseModel):
    decision: Literal["rerun", "hold", "escalate"]
    reason: str = Field(..., min_length=3, max_length=500)
    failure_class: Optional[Literal[
        "crm_contact_missing",
        "crm_write",
        "workflow",
        "rate_limit",
        "data_quality",
        "unknown",
    ]] = None


class FollowUpLifecycleRequest(BaseModel):
    stage: Literal[
        "queued",
        "outreach_sent",
        "responded",
        "next_step",
        "booked",
        "enrolled",
        "lost",
        "failed",
    ]
    reason: str = Field(..., min_length=3, max_length=500)
    next_step: Optional[str] = Field(None, max_length=500)
    enrollment_outcome: Optional[str] = Field(None, max_length=200)


def _audit(db: Session, current_user: Any, result_id: Any, event_type: str, details: dict[str, Any]) -> None:
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=result_id,
        event_type=event_type,
        details=details,
    ))
    db.commit()


def _create_operational_alert(
    db: Session,
    *,
    alert_type: str,
    source: str,
    message: str,
    result_id: Any = None,
    details: dict[str, Any] | None = None,
    severity: str = "critical",
) -> OperationalAlert:
    alert = OperationalAlert(
        alert_type=alert_type,
        source=source,
        message=message,
        result_id=result_id,
        details=details or {},
        severity=severity,
    )
    db.add(alert)
    return alert


def _record_ghl_writeback_failure(
    db: Session,
    current_user: Any,
    result: BatchExecutionResult,
    writeback: dict[str, Any],
) -> None:
    _create_operational_alert(
        db,
        alert_type="ghl_writeback_failure",
        source="ghl",
        message="Enrollment activity was recorded in ENY but could not be synchronized to GHL.",
        result_id=result.id,
        details={"contact_id": result.contact_id, "writeback": writeback},
    )
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=result.id,
        event_type="ghl_writeback_failed",
        details={"contact_id": result.contact_id, "writeback": writeback},
    ))


def _normalize_int(value: Any, default: int) -> int:
    if hasattr(value, "default"):
        value = getattr(value, "default")
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if hasattr(value, "default"):
        value = getattr(value, "default")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return default


def _query_default(value: Any) -> Any:
    return getattr(value, "default", value)


def _serialize_datetime(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _hours_since(value: Any) -> float:
    if value is None:
        return float("inf")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return float("inf")
        value = parsed
    if not hasattr(value, "tzinfo") or value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - value.astimezone(timezone.utc)).total_seconds() / 3600.0


def _transition_queue_state(
    result: BatchExecutionResult,
    target_state: str,
    actor_id: Any,
    reason: str,
) -> str:
    previous_state = getattr(result, "queue_status", "new")
    if target_state not in QUEUE_STATES:
        raise HTTPException(status_code=422, detail=f"Invalid queue state: {target_state}")
    if target_state not in QUEUE_TRANSITIONS.get(previous_state, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid queue transition: {previous_state} -> {target_state}",
        )
    result.queue_status = target_state
    result.last_action_at = datetime.now(timezone.utc)
    return previous_state


@router.post("/ghl-webhook", status_code=status.HTTP_202_ACCEPTED)
async def ingest_ghl_contact(
    payload: dict[str, Any],
    x_ghl_webhook_token: Optional[str] = Header(None, alias="X-GHL-Webhook-Token"),
    db: Session = Depends(get_db),
):
    """Queue a GHL contact for human cohort review; this endpoint never scores or messages it."""
    configured_token = settings.GHL_INBOUND_WEBHOOK_TOKEN
    if not configured_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GHL intake webhook is not configured")
    if not x_ghl_webhook_token or not hmac.compare_digest(x_ghl_webhook_token, configured_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GHL webhook token")

    contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else payload
    contact_id = (
        contact.get("id")
        or contact.get("contactId")
        or contact.get("contact_id")
        or payload.get("contactId")
        or payload.get("contact_id")
    )
    if not isinstance(contact_id, str) or not contact_id.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GHL webhook payload is missing a contact ID")

    source = contact.get("source") or payload.get("source")
    inserted_contact_id = db.execute(
        pg_insert(GHLLeadIntake)
        .values(contact_id=contact_id.strip(), source=str(source)[:200] if source else None)
        .on_conflict_do_nothing(index_elements=[GHLLeadIntake.contact_id])
        .returning(GHLLeadIntake.contact_id)
    ).scalar_one_or_none()
    db.commit()
    intake = db.query(GHLLeadIntake).filter(GHLLeadIntake.contact_id == contact_id.strip()).first()
    if not intake:
        logger.error("GHL intake insert returned no event for contact %s", contact_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to queue GHL contact for review")
    return {
        "status": intake.status,
        "contact_id": intake.contact_id,
        "duplicate": inserted_contact_id is None,
    }


@router.get("/intake/pending", dependencies=[Depends(require_permission("leads:read"))])
async def get_pending_ghl_intake(
    limit: int = Query(100, ge=1, le=250),
    db: Session = Depends(get_db),
):
    """List GHL arrivals waiting for a team member to approve a scoring batch."""
    rows = (
        db.query(GHLLeadIntake)
        .filter(GHLLeadIntake.status == "pending_review")
        .order_by(GHLLeadIntake.received_at.asc())
        .limit(limit)
        .all()
    )
    contacts, inventory = await ghl_service.get_all_contacts()
    contacts_by_id = {str(contact.get("id")): contact for contact in contacts if contact.get("id")}
    pending = []
    for row in rows:
        contact = contacts_by_id.get(str(row.contact_id), {})
        pending.append({
            "contact_id": row.contact_id,
            "name": contact.get("name") or " ".join(
                part for part in (contact.get("firstName"), contact.get("lastName")) if part
            ),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "source": row.source or contact.get("source") or "unknown",
            "tags": contact.get("tags") or [],
            "received_at": _serialize_datetime(row.received_at),
            "ghl_available": bool(contact),
        })
    return {"status": inventory.get("status", "unknown"), "leads": pending, "total": len(pending)}


@router.get("/metrics", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get enrollment dashboard metrics.
    Requires leads:read permission.
    """
    try:
        contacts, inventory = await ghl_service.get_all_contacts()
        pipeline = await ghl_service.get_pipeline_data()
        hot_count = db.query(func.count(BatchExecutionResult.id)).filter(
            BatchExecutionResult.category == "hot",
            BatchExecutionResult.queue_status != "closed",
        ).scalar() or 0
        pending_retries = db.query(func.count(BatchExecutionResult.id)).filter(
            BatchExecutionResult.status == "failed",
        ).scalar() or 0
        metrics = {
            "totalLeads": len(contacts),
            "newLeadsToday": len([
                contact for contact in contacts
                if str(contact.get("dateAdded", ""))[:10] == datetime.now(timezone.utc).date().isoformat()
            ]),
            "conversionRate": round(float(pipeline.get("conversion_rate", 0)) * 100, 2),
            "revenuePipeline": pipeline.get("revenue_forecast", 0),
            "hotLeads": hot_count,
            "retryPending": pending_retries,
            "crmStatus": inventory.get("status", "unknown"),
        }
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching enrollment metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )

@router.get("/leads", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_leads(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    mine: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """
    Get GHL leads with ENY assignment metadata.
    Requires leads:read permission.
    """
    try:
        assigned_contact_ids: set[str] | None = None
        if mine:
            assignments = (
                db.query(LeadAssignment.contact_id)
                .filter(LeadAssignment.assigned_user_id == current_user.id)
                .all()
            )
            assigned_contact_ids = {str(row[0]) for row in assignments}
            if not assigned_contact_ids:
                return {
                    "leads": [],
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                    "search": search or "",
                    "mine": True,
                    "has_more": False,
                }

        leads = await ghl_service.get_enrollment_leads(
            limit=limit + 1,
            search=search or "",
            contact_ids=assigned_contact_ids,
            offset=offset,
        )
        has_more = len(leads) > limit
        leads = leads[:limit]
        contact_ids = [str(lead["id"]) for lead in leads if lead.get("id")]
        assignments = (
            db.query(LeadAssignment)
            .filter(LeadAssignment.contact_id.in_(contact_ids))
            .all()
        ) if contact_ids else []
        assignment_by_contact = {assignment.contact_id: assignment for assignment in assignments}
        for lead in leads:
            assignment = assignment_by_contact.get(str(lead.get("id") or ""))
            lead["assigned_user_id"] = str(assignment.assigned_user_id) if assignment else None
            lead["assigned_department"] = assignment.assigned_department if assignment else None
        return {
            "leads": leads,
            "total": len(leads),
            "limit": limit,
            "offset": offset,
            "search": search or "",
            "mine": mine,
            "has_more": has_more,
        }
    except Exception as e:
        logger.error(f"Error fetching enrollment leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch leads: {str(e)}"
        )


@router.patch(
    "/leads/{contact_id}/assignment",
    dependencies=[Depends(require_permission("leads:write"))],
)
async def assign_enrollment_crm_lead(
    contact_id: str,
    request: LeadAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Assign a GHL contact without duplicating its CRM record in ENY."""
    departments = _assignment_departments(db, current_user.id, "/api/v1/enrollment/leads/{contact_id}/assignment")
    if request.department is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A Sales or Enrollment department is required",
        )
    if request.department not in departments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot assign leads outside your department",
        )

    existing_assignment = (
        db.query(LeadAssignment)
        .filter(LeadAssignment.contact_id == contact_id)
        .first()
    )
    if existing_assignment and existing_assignment.assigned_department not in departments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot reassign a lead owned by another department",
        )

    eligible_user = (
        db.query(UserRole.user_id)
        .join(Role, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == request.assigned_user_id)
        .filter(Role.name.in_((request.department, f"{request.department}_lead")))
        .first()
    )
    if not eligible_user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Lead can only be assigned to a {request.department.title()} team member",
        )

    contact = await ghl_service.get_contact(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to verify this lead with GHL. Refresh the lead list and try again.",
        )

    previous_owner_id = _record_lead_assignment(
        db,
        contact_id=contact_id,
        assigned_user_id=request.assigned_user_id,
        assigned_department=request.department,
        assigned_by_user_id=current_user.id,
    )
    batch_results = (
        db.query(BatchExecutionResult)
        .filter(BatchExecutionResult.contact_id == contact_id)
        .all()
    )
    for result in batch_results:
        if getattr(result, "queue_status", "new") == "new":
            _transition_queue_state(
                result,
                "assigned",
                current_user.id,
                "Assigned for active Sales and Enrollment follow-up",
            )
        result.assigned_user_id = request.assigned_user_id
        result.assigned_department = request.department
        if result.category == "hot":
            db.add(EnrollmentAudit(
                user_id=current_user.id,
                result_id=result.id,
                event_type="hot_lead_assigned",
                details={
                    "contact_id": contact_id,
                    "department": request.department,
                    "assigned_user_id": str(request.assigned_user_id),
                    "actor_id": str(current_user.id),
                    "reason": "Lead assigned from the GHL lead inventory",
                },
            ))
    _audit(db, current_user, None, "lead_assignment_changed", {
        "contact_id": contact_id,
        "department": request.department,
        "from_owner_id": str(previous_owner_id) if previous_owner_id else None,
        "assigned_user_id": str(request.assigned_user_id),
        "actor_id": str(current_user.id),
    })
    return {
        "contact_id": contact_id,
        "assigned_user_id": str(request.assigned_user_id),
        "department": request.department,
    }


@router.get("/hot-leads", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_hot_leads(
    limit: int = Query(20, ge=1, le=100),
    min_score: int = Query(85, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the current hot-lead queue sourced from approved execution results."""
    try:
        limit = _normalize_int(limit, 20)
        min_score = _normalize_int(min_score, 85)
        current_user_id = str(current_user.id)

        rows = (
            db.query(BatchExecutionResult)
            .filter(BatchExecutionResult.category == "hot")
            .filter(BatchExecutionResult.score >= min_score)
            .filter(
                (BatchExecutionResult.status.in_(["scored", "queued", "hot"]))
                | (BatchExecutionResult.assigned_user_id == current_user_id)
            )
            .order_by(BatchExecutionResult.created_at.desc())
            .limit(limit)
            .all()
        )

        result_ids = [row.id for row in rows]
        audit_rows = (
            db.query(EnrollmentAudit)
            .filter(EnrollmentAudit.result_id.in_(result_ids))
            .order_by(EnrollmentAudit.created_at.desc())
            .all()
        ) if result_ids else []
        follow_up_alerts = (
            db.query(OperationalAlert)
            .filter(
                OperationalAlert.result_id.in_(result_ids),
                OperationalAlert.alert_type.in_(["n8n_webhook_failure", "follow_up_tag_failure"]),
            )
            .order_by(OperationalAlert.created_at.desc())
            .all()
        ) if result_ids else []
        latest_comments: dict[str, str] = {}
        retry_approved: dict[str, bool] = {}
        for event in audit_rows:
            result_key = str(getattr(event, "result_id", ""))
            details = getattr(event, "details", {}) or {}
            if result_key and result_key not in latest_comments and isinstance(details, dict):
                comment = details.get("reason") or details.get("comment") or details.get("next_step")
                if comment:
                    latest_comments[result_key] = str(comment)
        for alert in follow_up_alerts:
            result_key = str(getattr(alert, "result_id", "") or "")
            if result_key and result_key not in retry_approved:
                retry_approved[result_key] = alert.status == "acknowledged"

        leads = [
            {
                "id": str(row.contact_id),
                "result_id": str(row.id),
                "contact_id": row.contact_id,
                "firstName": (row.contact_name or "").split(" ")[0] if row.contact_name else "",
                "lastName": " ".join((row.contact_name or "").split(" ")[1:]) if row.contact_name else "",
                "email": row.email,
                "phone": row.phone,
                "score": row.score,
                "score_origin": getattr(row, "score_origin", "unknown"),
                "score_reasoning": getattr(row, "score_reasoning", None),
                "score_factors": getattr(row, "score_factors", None),
                "score_evidence": getattr(row, "score_evidence", None),
                "score_unknowns": getattr(row, "score_unknowns", None),
                "next_best_action": getattr(row, "next_best_action", None),
                "source": getattr(row, "source", None),
                "tags": row.tags or [row.category or "hot"],
                "category": row.category,
                "approval_id": str(row.approval_id) if row.approval_id else None,
                "status": getattr(row, "queue_status", "new"),
                "lifecycle_stage": getattr(row, "lifecycle_stage", "not_started"),
                "next_step": getattr(row, "next_step", None),
                "assigned_user_id": str(row.assigned_user_id) if row.assigned_user_id else None,
                "last_comment": latest_comments.get(str(row.id)),
                "follow_up_retry_approved": retry_approved.get(str(row.id), False),
                "follow_up_status": getattr(row, "follow_up_status", "not_started"),
                "assigned_to_current_user": (
                    str(row.assigned_user_id) == current_user_id
                    if row.assigned_user_id
                    else False
                ),
                "execution_status": row.status,
                "created_at": _serialize_datetime(getattr(row, "created_at", None)),
            }
            for row in rows
        ]
        return {"leads": leads, "total": len(leads), "limit": limit, "min_score": min_score}
    except Exception as e:
        logger.error(f"Error fetching hot leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch hot leads: {str(e)}",
        )


@router.get(
    "/team-members",
    dependencies=[Depends(require_permission("leads:write"))],
)
async def get_enrollment_team_members(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Return the team members the caller is authorized to assign leads to."""
    departments = _assignment_departments(db, current_user.id, "/api/v1/enrollment/team-members")
    if not departments:
        return {"members": []}

    role_to_department = {
        "sales": "sales",
        "sales_lead": "sales",
        "enrollment": "enrollment",
        "enrollment_lead": "enrollment",
    }
    role_user_rows = (
        db.query(UserRole.user_id, Role.name)
        .join(Role, UserRole.role_id == Role.id)
        .filter(Role.name.in_(tuple(role_to_department)))
        .all()
    )
    eligible_departments: dict[str, set[str]] = {}
    for user_id, role_name in role_user_rows:
        department = role_to_department[role_name]
        if department in departments:
            eligible_departments.setdefault(str(user_id), set()).add(department)
    if not eligible_departments:
        return {"members": []}

    try:
        auth_users = await supabase_admin_service.list_users()
    except Exception as exc:
        logger.error("Unable to load Sales & Enrollment team members from Supabase Auth: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to load Sales & Enrollment team members",
        ) from exc

    members = []
    for user in auth_users:
        user_id = str(user.get("id") or "")
        if user_id not in eligible_departments:
            continue
        metadata = user.get("user_metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        email = str(user.get("email") or "")
        name = (
            metadata.get("full_name")
            or metadata.get("name")
            or metadata.get("display_name")
            or email
            or user_id
        )
        for department in sorted(eligible_departments[user_id]):
            members.append({
                "id": user_id,
                "name": str(name),
                "email": email or None,
                "department": department,
            })

    members.sort(key=lambda member: (member["department"], member["name"].casefold()))
    return {"members": members}


@router.patch(
    "/hot-leads/{result_id}/assignment",
    dependencies=[Depends(require_permission("leads:write"))],
)
async def assign_hot_lead(
    result_id: UUID,
    request: LeadAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Assign a hot lead within the caller's Sales or Enrollment department."""
    departments = _assignment_departments(db, current_user.id, "/api/v1/enrollment/hot-leads/{result_id}/assignment")
    if not departments:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Lead assignment is not permitted")

    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hot lead not found")
    if result.category != "hot" or result.queue_status == "closed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lead is not available for assignment")
    if (
        getattr(result, "assigned_department", None)
        and result.assigned_department not in departments
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot reassign a lead owned by another department",
        )

    department = request.department
    if department is None:
        target_roles = (
            db.query(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == request.assigned_user_id)
            .filter(Role.name.in_(("sales", "sales_lead", "enrollment", "enrollment_lead")))
            .all()
        )
        target_departments = {
            "sales" if role_name in {"sales", "sales_lead"} else "enrollment"
            for (role_name,) in target_roles
        }
        if len(target_departments) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Specify the lead's department when the assignee belongs to multiple teams",
            )
        department = target_departments.pop()

    if department not in departments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot assign leads outside your department",
        )

    eligible_user = (
        db.query(UserRole.user_id)
        .join(Role, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == request.assigned_user_id)
        .filter(Role.name.in_((department, f"{department}_lead")))
        .first()
    )
    if not eligible_user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Lead can only be assigned to a {department.title()} team member",
        )

    assigned_user_id = str(request.assigned_user_id)
    if (
        str(result.assigned_user_id or "") == assigned_user_id
        and getattr(result, "assigned_department", None) == department
    ):
        return {
            "status": result.queue_status,
            "result_id": str(result.id),
            "assigned_user_id": assigned_user_id,
            "department": department,
        }

    target_state = "assigned" if result.queue_status == "new" else result.queue_status
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status=target_state,
        note=f"ENY Enrollment lead assigned to team member {assigned_user_id}.",
    )
    if not writeback.get("success"):
        _record_ghl_writeback_failure(db, current_user, result, writeback)

    previous_owner_id = str(result.assigned_user_id) if result.assigned_user_id else None
    if result.queue_status == "new":
        _transition_queue_state(result, "assigned", current_user.id, "Assigned for active enrollment follow-up")
    result.assigned_user_id = request.assigned_user_id
    result.assigned_department = department
    assignment_previous_owner_id = _record_lead_assignment(
        db,
        contact_id=result.contact_id,
        assigned_user_id=request.assigned_user_id,
        assigned_department=department,
        assigned_by_user_id=current_user.id,
    )
    if assignment_previous_owner_id:
        previous_owner_id = str(assignment_previous_owner_id)
    _audit(db, current_user, result.id, "hot_lead_assigned", {
        "contact_id": result.contact_id,
        "department": department,
        "from_owner_id": previous_owner_id,
        "assigned_user_id": assigned_user_id,
        "actor_id": str(current_user.id),
        "reason": "Lead assigned to a Sales & Enrollment team member",
        "ghl_writeback": writeback,
    })
    return {
        "status": result.queue_status,
        "result_id": str(result.id),
        "assigned_user_id": assigned_user_id,
        "department": department,
        "ghl_writeback": writeback,
        "warning": None if writeback.get("success") else "Lead was assigned in ENY, but GHL synchronization failed.",
    }


@router.get("/batch-results", dependencies=[Depends(require_permission("leads:read"))])
async def get_batch_execution_results(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the approved batch execution ledger for review and retry tracking."""
    try:
        limit = _normalize_int(limit, 20)

        rows = (
            db.query(BatchExecutionResult)
            .order_by(BatchExecutionResult.created_at.desc())
            .limit(limit)
            .all()
        )

        summary_rows = db.query(BatchExecutionResult).all()
        summary = {
            "total": len(summary_rows),
            "succeeded": len([row for row in summary_rows if row.status in {"scored", "already_scored"}]),
            "pending": len([row for row in summary_rows if row.status in {"pending", "queued"}]),
            "failed": len([row for row in summary_rows if row.status == "failed"]),
            "exhausted": len([row for row in summary_rows if row.status == "exhausted"]),
            "held": len([row for row in summary_rows if row.status == "held"]),
            "escalated": len([row for row in summary_rows if row.status == "escalated"]),
            "rerun_approved": len([row for row in summary_rows if getattr(row, "operating_decision", "hold") == "rerun"]),
        }

        results = [
            {
                "id": str(row.id),
                "approval_id": str(row.approval_id) if row.approval_id else None,
                "cohort_name": row.cohort_name,
                "contact_id": row.contact_id,
                "contact_name": getattr(row, "contact_name", None),
                "email": getattr(row, "email", None),
                "phone": getattr(row, "phone", None),
                "source": getattr(row, "source", None),
                "score": row.score,
                "category": row.category,
                "status": row.status,
                "error": row.error,
                "retry_count": row.retry_count,
                "operating_decision": getattr(row, "operating_decision", "hold"),
                "failure_class": getattr(row, "failure_class", None),
                "recovery_owner_id": str(row.recovery_owner_id) if getattr(row, "recovery_owner_id", None) else None,
                "recovery_status": getattr(row, "recovery_status", "unassigned"),
                "created_at": _serialize_datetime(getattr(row, "created_at", None)),
            }
            for row in rows
        ]
        return {"results": results, "total": len(results), "limit": limit, "summary": summary}
    except Exception as e:
        logger.error(f"Error fetching batch execution results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch batch execution results: {str(e)}",
        )


@router.get("/operations", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_operations(
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    mine: bool = Query(False),
    unassigned: bool = Query(False),
    assigned_only: bool = Query(False, alias="assigned"),
    source: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Return the shared Enrollment follow-up queue and its recent audit trail."""
    status_filter = _query_default(status_filter)
    source = _query_default(source)
    min_score = _query_default(min_score)
    max_score = _query_default(max_score)
    query = db.query(BatchExecutionResult)
    assignment_departments = _assignment_departments(db, current_user.id, "/api/v1/enrollment/operations")
    if len(assignment_departments) == 1:
        department = next(iter(assignment_departments))
        query = query.filter(or_(
            BatchExecutionResult.assigned_department == department,
            BatchExecutionResult.assigned_user_id.is_(None),
        ))
    if status_filter:
        query = query.filter(BatchExecutionResult.queue_status == status_filter)
    if mine:
        query = query.filter(BatchExecutionResult.assigned_user_id == current_user.id)
    if unassigned:
        query = query.filter(BatchExecutionResult.assigned_user_id.is_(None))
    if _normalize_bool(assigned_only):
        query = query.filter(BatchExecutionResult.assigned_user_id.is_not(None))
    if source:
        query = query.filter(BatchExecutionResult.source == source)
    if min_score is not None:
        query = query.filter(BatchExecutionResult.score >= min_score)
    if max_score is not None:
        query = query.filter(BatchExecutionResult.score <= max_score)
    results = query.order_by(BatchExecutionResult.created_at.desc()).limit(limit).all()
    monitoring_rows = db.query(BatchExecutionResult).all()
    audits = db.query(EnrollmentAudit).order_by(
        EnrollmentAudit.created_at.desc()
    ).limit(limit).all()
    latest_comments: dict[str, str] = {}
    for event in audits:
        result_key = str(getattr(event, "result_id", "") or "")
        details = getattr(event, "details", {}) or {}
        if result_key and result_key not in latest_comments and isinstance(details, dict):
            comment = details.get("reason") or details.get("comment") or details.get("next_step")
            if comment:
                latest_comments[result_key] = str(comment)

    try:
        contacts, inventory = await ghl_service.get_all_contacts()
        crm_status = inventory.get("status", "connected") if isinstance(inventory, dict) else "connected"
    except Exception:
        contacts = []
        crm_status = "degraded"

    summary = {
        "total": len(results),
        "new": len([row for row in results if getattr(row, "queue_status", "new") == "new"]),
        "assigned": len([row for row in results if getattr(row, "queue_status", "new") == "assigned"]),
        "contacted": len([row for row in results if getattr(row, "queue_status", "new") == "contacted"]),
        "qualified": len([row for row in results if getattr(row, "queue_status", "new") == "qualified"]),
        "closed": len([row for row in results if getattr(row, "queue_status", "new") == "closed"]),
        "follow_up_failed": len([row for row in results if getattr(row, "follow_up_status", "not_started") == "failed"]),
        "new_hot": len([row for row in results if getattr(row, "queue_status", "new") == "new" and row.category == "hot"]),
        "my_assigned": len([row for row in results if str(getattr(row, "assigned_user_id", "")) == str(current_user.id)]),
        "uncontacted_assigned": len([row for row in results if getattr(row, "queue_status", "new") == "assigned"]),
        "ownerless_leads": len([
            row for row in results
            if row.category == "hot" and getattr(row, "assigned_user_id", None) is None
        ]),
        "stale_leads": len([
            row for row in results
            if getattr(row, "queue_status", "new") in {"new", "assigned", "contacted"}
            and _hours_since(getattr(row, "last_action_at", None) or getattr(row, "updated_at", None) or getattr(row, "created_at", None)) > 24
        ]),
        "data_quality_alerts": len([
            row for row in results
            if (not getattr(row, "email", None) and not getattr(row, "phone", None))
            or (not getattr(row, "contact_name", None) and not getattr(row, "email", None))
        ]),
        "contacted_today": len([
            row for row in results
            if getattr(row, "queue_status", "") == "contacted"
            and getattr(row, "follow_up_at", None)
            and row.follow_up_at.date() == datetime.now(timezone.utc).date()
        ]),
        "workflow_failures": len([row for row in results if getattr(row, "error", None) or getattr(row, "follow_up_status", "") == "failed"]),
    }
    response_times = [
        (row.follow_up_at - row.created_at).total_seconds() / 60
        for row in results
        if getattr(row, "follow_up_at", None) and getattr(row, "created_at", None)
    ]
    summary["average_response_minutes"] = round(sum(response_times) / len(response_times)) if response_times else 0

    now = datetime.now(timezone.utc)
    today = now.date()
    yesterday = today - timedelta(days=1)
    intake_today = len([
        row for row in monitoring_rows
        if getattr(row, "created_at", None) and row.created_at.date() == today
    ])
    intake_yesterday = len([
        row for row in monitoring_rows
        if getattr(row, "created_at", None) and row.created_at.date() == yesterday
    ])
    no_contact_rows = [
        row for row in monitoring_rows
        if getattr(row, "queue_status", "new") in {"new", "assigned"}
        and not getattr(row, "follow_up_at", None)
    ]
    no_contact_aging = {
        "under_1_hour": len([row for row in no_contact_rows if _hours_since(getattr(row, "created_at", None)) < 1]),
        "one_to_four_hours": len([row for row in no_contact_rows if 1 <= _hours_since(getattr(row, "created_at", None)) < 4]),
        "four_to_twenty_four_hours": len([row for row in no_contact_rows if 4 <= _hours_since(getattr(row, "created_at", None)) < 24]),
        "over_24_hours": len([row for row in no_contact_rows if _hours_since(getattr(row, "created_at", None)) >= 24]),
    }
    source_groups: dict[str, list[Any]] = {}
    for row in monitoring_rows:
        source_groups.setdefault(getattr(row, "source", None) or "unknown", []).append(row)
    conversion_by_source = {
        source_name: {
            "total": len(source_rows),
            "contacted": len([row for row in source_rows if getattr(row, "queue_status", "new") in {"contacted", "qualified", "closed"}]),
            "qualified": len([row for row in source_rows if getattr(row, "queue_status", "new") in {"qualified", "closed"}]),
            "closed": len([row for row in source_rows if getattr(row, "queue_status", "new") == "closed"]),
            "conversion_percent": round(
                len([row for row in source_rows if getattr(row, "queue_status", "new") == "closed"]) / len(source_rows) * 100
            ) if source_rows else 0,
        }
        for source_name, source_rows in sorted(source_groups.items())
    }
    owner_groups: dict[str, list[Any]] = {}
    for row in monitoring_rows:
        owner_groups.setdefault(str(getattr(row, "assigned_user_id", None) or "unassigned"), []).append(row)
    owner_workload = [
        {
            "owner_id": owner_id,
            "total": len(owner_rows),
            "active": len([row for row in owner_rows if getattr(row, "queue_status", "new") != "closed"]),
            "stale": len([row for row in owner_rows if getattr(row, "queue_status", "new") in {"new", "assigned", "contacted"} and _hours_since(getattr(row, "last_action_at", None) or getattr(row, "created_at", None)) > 24]),
        }
        for owner_id, owner_rows in sorted(owner_groups.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    monitoring = {
        "generated_at": now.isoformat(),
        "lead_intake": {
            "today": intake_today,
            "yesterday": intake_yesterday,
            "change_percent": round((intake_today - intake_yesterday) / intake_yesterday * 100) if intake_yesterday else None,
        },
        "stale_leads": summary["stale_leads"],
        "no_contact_aging": no_contact_aging,
        "conversion_by_source": conversion_by_source,
        "owner_workload": owner_workload,
    }

    def alert(severity: str, code: str, message: str, count: int, action: str) -> dict[str, Any] | None:
        if count == 0:
            return None
        return {
            "severity": severity,
            "code": code,
            "message": message,
            "count": count,
            "action": action,
        }

    ownerless_count = summary["ownerless_leads"]
    stale_count = summary["stale_leads"]
    quality_count = summary["data_quality_alerts"]
    failure_count = summary["workflow_failures"]
    alerts = [
        alert("critical", "ownerless_hot_leads", "Hot leads have no owner.", ownerless_count, "Claim or assign each lead."),
        alert("warning", "stale_queue_work", "Queue work has exceeded its response window.", stale_count, "Review stale leads and record the next action."),
        alert("warning", "data_quality", "Leads are missing a usable contact channel.", quality_count, "Correct the contact record in GHL."),
        alert("critical", "workflow_failures", "Scoring or follow-up workflows need attention.", failure_count, "Review the error and retry when safe."),
    ]

    tracked_response_rows = [
        row for row in results
        if getattr(row, "follow_up_at", None) and getattr(row, "created_at", None)
    ]
    compliant_response_rows = [
        row for row in tracked_response_rows
        if 0 <= (row.follow_up_at - row.created_at).total_seconds() / 60
        <= SLA_RULES["assigned_contact_minutes"]
    ]
    response_compliance = round((len(compliant_response_rows) / len(tracked_response_rows)) * 100) if tracked_response_rows else 0

    queue_health = "healthy"
    if crm_status != "connected":
        queue_health = "degraded"
    elif summary["ownerless_leads"] > 0 or summary["stale_leads"] > 0 or summary["data_quality_alerts"] > 0:
        queue_health = "warning"
    if summary["workflow_failures"] > 0 and summary["stale_leads"] > 0:
        queue_health = "degraded"

    reporting = {
        "window": "current queue",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "response_compliance_percent": response_compliance,
        "average_response_minutes": summary["average_response_minutes"],
        "closed_leads": summary["closed"],
        "workflow_success_percent": round(
            ((summary["total"] - failure_count) / summary["total"]) * 100
        ) if summary["total"] else 100,
    }
    rollout = {
        "status": "ready" if queue_health == "healthy" else "needs_attention",
        "team": "Sales & Enrollment",
        "sop_route": "/dashboard/writer",
        "training_focus": "Claim leads, meet response SLAs, record next action, and resolve alerts.",
        "open_alerts": len([item for item in alerts if item]),
    }

    def next_action(row: BatchExecutionResult) -> str:
        if row.error or getattr(row, "follow_up_status", "") == "failed":
            return "Review error and retry"
        return {
            "new": "Claim lead",
            "assigned": "Notify Sales & Enrollment",
            "contacted": "Qualify lead",
            "qualified": "Close lead",
            "closed": "Complete",
        }.get(getattr(row, "queue_status", "new"), "Review lead")

    def retry_available(row: BatchExecutionResult) -> bool:
        return row.status == "failed"

    return {
        "summary": summary,
        "health": {
            "queue_health": queue_health,
            "crm_status": crm_status,
            "contacts_checked": len(contacts),
            "ownerless_leads": summary["ownerless_leads"],
            "stale_leads": summary["stale_leads"],
            "data_quality_alerts": summary["data_quality_alerts"],
        },
        "sla": {
            "rules": SLA_RULES,
            "alerts": [item for item in alerts if item],
        },
        "reporting": reporting,
        "monitoring": monitoring,
        "rollout": rollout,
        "results": [
            {
                "id": str(row.id),
                "contact_id": row.contact_id,
                "contact_name": row.contact_name,
                "email": row.email,
                "phone": row.phone,
                "source": row.source,
                "score": row.score,
                "category": row.category,
                "execution_status": row.status,
                "queue_status": getattr(row, "queue_status", "new"),
                "assigned_user_id": str(row.assigned_user_id) if getattr(row, "assigned_user_id", None) else None,
                "assigned_department": getattr(row, "assigned_department", None),
                "last_comment": latest_comments.get(str(row.id)),
                "follow_up_status": getattr(row, "follow_up_status", "not_started"),
                "follow_up_at": _serialize_datetime(getattr(row, "follow_up_at", None)),
                "lifecycle_stage": getattr(row, "lifecycle_stage", "not_started"),
                "next_step": getattr(row, "next_step", None),
                "response_at": _serialize_datetime(getattr(row, "response_at", None)),
                "booked_at": _serialize_datetime(getattr(row, "booked_at", None)),
                "enrollment_outcome": getattr(row, "enrollment_outcome", None),
                "error": row.error,
                "retry_count": row.retry_count,
                "score_origin": getattr(row, "score_origin", "approved_batch"),
                "notification_status": getattr(row, "notification_status", "not_attempted"),
                "notification_error": getattr(row, "notification_error", None),
                "last_action_at": _serialize_datetime(getattr(row, "last_action_at", None) or getattr(row, "updated_at", None) or row.created_at),
                "retry_available": retry_available(row),
                "operating_decision": getattr(row, "operating_decision", "hold"),
                "failure_class": getattr(row, "failure_class", None),
                "recovery_owner_id": str(row.recovery_owner_id) if getattr(row, "recovery_owner_id", None) else None,
                "recovery_status": getattr(row, "recovery_status", "unassigned"),
                "next_action": next_action(row),
                "score_reasoning": getattr(row, "score_reasoning", None),
                "score_factors": getattr(row, "score_factors", None),
                "score_evidence": getattr(row, "score_evidence", None),
                "score_unknowns": getattr(row, "score_unknowns", None),
                "next_best_action": getattr(row, "next_best_action", None),
                "ghl_contact_reference": row.contact_id,
                "created_at": _serialize_datetime(row.created_at),
            }
            for row in results
        ],
        "audit_events": [
            {
                "id": str(event.id),
                "result_id": str(event.result_id) if event.result_id else None,
                "user_id": str(event.user_id),
                "event_type": event.event_type,
                "details": event.details,
                "created_at": _serialize_datetime(event.created_at),
            }
            for event in audits
        ],
    }


@router.patch("/batch-results/{result_id}/decision", dependencies=[Depends(require_permission("leads:write"))])
async def decide_batch_result(
    result_id: UUID,
    request: BatchDecisionRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Record the operator decision for a failed result without executing external work."""
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch result not found")

    approval = db.query(CohortApproval).filter(
        CohortApproval.id == result.approval_id,
        CohortApproval.user_id == current_user.id,
    ).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval record not found")
    if result.status not in {"failed", "missing_in_ghl", "held", "escalated", "exhausted"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed batch results can receive a recovery decision")
    if request.decision == "rerun" and result.status == "exhausted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maximum retry attempts reached; escalate this result")

    pending_retry = db.query(BatchRetry).filter(
        BatchRetry.result_id == result.id,
        BatchRetry.status.in_(["retry_pending", "held", "escalated"]),
    ).order_by(BatchRetry.created_at.desc()).first()
    if request.decision == "rerun" and not pending_retry:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No retry record is available for this result")

    result.operating_decision = request.decision
    result.failure_class = request.failure_class or getattr(result, "failure_class", None) or "unknown"
    result.recovery_owner_id = current_user.id
    result.recovery_status = "assigned" if request.decision == "rerun" else request.decision
    result.last_action_at = datetime.now(timezone.utc)
    if request.decision == "hold":
        result.status = "held"
    elif request.decision == "escalate":
        result.status = "escalated"
    if pending_retry:
        pending_retry.operating_decision = request.decision
        pending_retry.failure_class = result.failure_class
        pending_retry.recovery_owner_id = current_user.id
        pending_retry.status = "retry_pending" if request.decision == "rerun" else request.decision
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=result.id,
        event_type="batch_recovery_decision",
        details={
            "decision": request.decision,
            "failure_class": result.failure_class,
            "reason": request.reason,
            "recovery_owner_id": str(current_user.id),
        },
    ))
    db.commit()
    return {
        "status": result.status,
        "result_id": str(result.id),
        "decision": result.operating_decision,
        "failure_class": result.failure_class,
        "recovery_owner_id": str(result.recovery_owner_id),
    }


@router.post("/batch-results/{result_id}/retry", dependencies=[Depends(require_permission("leads:write"))])
async def retry_enrollment_batch_result(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retry one failed result from its original, user-owned approved cohort."""
    result = db.query(BatchExecutionResult).filter(
        BatchExecutionResult.id == result_id,
    ).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch result not found")

    approval = db.query(CohortApproval).filter(
        CohortApproval.id == result.approval_id,
        CohortApproval.user_id == current_user.id,
    ).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval record not found")
    if getattr(approval, "decision", "approved") != "approved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The parent approval is not approved for recovery")
    if getattr(result, "operating_decision", "hold") != "rerun":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Record an explicit rerun decision before retrying")
    if result.status != "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed results can be retried")
    if str(result.contact_id) not in {str(contact_id) for contact_id in (approval.contact_ids or [])}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Contact is outside the original approved batch")

    pending_retry = db.query(BatchRetry).filter(
        BatchRetry.result_id == result.id,
        BatchRetry.status == "retry_pending",
    ).order_by(BatchRetry.created_at.desc()).first()
    if not pending_retry:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This batch result is not waiting for retry",
        )
    if getattr(pending_retry, "operating_decision", "hold") != "rerun":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The retry is not approved to run")
    if pending_retry.next_attempt_at and pending_retry.next_attempt_at > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Retry is scheduled for {pending_retry.next_attempt_at.isoformat()}",
        )

    return await retry_batch_result(result, approval, db)


@router.patch("/hot-leads/{result_id}/lifecycle", dependencies=[Depends(require_permission("leads:write"))])
async def update_follow_up_lifecycle(
    result_id: UUID,
    request: FollowUpLifecycleRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Record the next authenticated step; enrollment does not itself verify payment or onboard a learner."""
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hot lead not found")
    if not result.assigned_user_id or str(result.assigned_user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim the lead before updating follow-up")

    previous_stage = getattr(result, "lifecycle_stage", "not_started")
    if request.stage not in LIFECYCLE_STAGES or request.stage not in LIFECYCLE_TRANSITIONS.get(previous_stage, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid follow-up lifecycle transition: {previous_stage} -> {request.stage}",
        )

    now = datetime.now(timezone.utc)
    target_queue_status = "contacted" if request.stage == "outreach_sent" else result.queue_status
    if request.stage == "outreach_sent":
        _transition_queue_state(result, "contacted", current_user.id, "Human outreach recorded as sent")
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status=target_queue_status,
        owner_id=str(current_user.id),
        note=f"ENY Enrollment lifecycle changed to {request.stage}: {request.reason}",
    )
    if not writeback.get("success"):
        _record_ghl_writeback_failure(db, current_user, result, writeback)

    result.lifecycle_stage = request.stage
    result.lifecycle_updated_at = now
    if request.stage == "outreach_sent":
        result.follow_up_at = now
    result.next_step = request.next_step
    result.enrollment_outcome = request.enrollment_outcome
    if request.stage == "responded":
        result.response_at = now
    if request.stage == "booked":
        result.booked_at = now
    if request.stage == "enrolled":
        result.enrollment_outcome = request.enrollment_outcome or "enrolled"
    if request.stage == "lost":
        result.enrollment_outcome = request.enrollment_outcome or "lost"

    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=result.id,
        event_type="follow_up_lifecycle_changed",
        details={
            "from": previous_stage,
            "to": request.stage,
            "reason": request.reason,
            "next_step": request.next_step,
            "enrollment_outcome": result.enrollment_outcome,
            "ghl_writeback": writeback,
        },
    ))
    db.commit()
    return {
        "result_id": str(result.id),
        "lifecycle_stage": result.lifecycle_stage,
        "queue_status": result.queue_status,
        "next_step": result.next_step,
        "response_at": _serialize_datetime(result.response_at),
        "booked_at": _serialize_datetime(result.booked_at),
        "enrollment_outcome": result.enrollment_outcome,
        "programs_handoff": "not_triggered",
        "ghl_writeback": writeback,
        "warning": None if writeback.get("success") else "Lifecycle was saved in ENY, but GHL synchronization failed.",
    }


@router.post("/hot-leads/{result_id}/claim", dependencies=[Depends(require_permission("leads:write"))])
async def claim_hot_lead(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Assign one hot lead to the authenticated Enrollment user."""
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Hot lead not found")
    if result.category != "hot" or result.queue_status == "closed":
        raise HTTPException(status_code=409, detail="Lead is not available for claiming")
    current_user_id = str(current_user.id)
    if result.assigned_user_id and str(result.assigned_user_id) != current_user_id:
        raise HTTPException(status_code=409, detail="Lead is already assigned to another Enrollment user")
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status="assigned",
        owner_id=current_user_id,
        note=f"ENY Enrollment lead assigned to owner {current_user_id}.",
    )
    if not writeback.get("success"):
        _record_ghl_writeback_failure(db, current_user, result, writeback)
    previous_state = _transition_queue_state(result, "assigned", current_user.id, "Claimed for active enrollment follow-up")
    result.assigned_user_id = current_user.id
    _audit(db, current_user, result.id, "hot_lead_claimed", {
        "contact_id": result.contact_id,
        "from": previous_state,
        "to": result.queue_status,
        "reason": "Claimed for active enrollment follow-up",
        "ghl_writeback": writeback,
    })
    return {
        "status": result.queue_status,
        "result_id": str(result.id),
        "assigned_user_id": str(current_user.id),
        "ghl_writeback": writeback,
        "warning": None if writeback.get("success") else "Lead was assigned in ENY, but GHL synchronization failed.",
    }


@router.patch("/hot-leads/{result_id}/state", dependencies=[Depends(require_permission("leads:write"))])
async def update_hot_lead_state(
    result_id: UUID,
    request: QueueStateRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Move an owned hot lead through the Enrollment queue state machine."""
    if request.state not in QUEUE_STATES:
        raise HTTPException(status_code=422, detail=f"Invalid queue state: {request.state}")
    result = db.query(BatchExecutionResult).filter(BatchExecutionResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Hot lead not found")
    if not result.assigned_user_id or str(result.assigned_user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Claim the lead before changing its state")
    previous_state = result.queue_status
    if request.state not in QUEUE_STATES or request.state not in QUEUE_TRANSITIONS.get(previous_state, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Invalid queue transition: {previous_state} -> {request.state}")
    writeback = await ghl_service.sync_enrollment_outcome(
        str(result.contact_id),
        queue_status=request.state,
        owner_id=str(current_user.id),
        note=f"ENY Enrollment queue status changed to {request.state}: {request.reason}",
    )
    if not writeback.get("success"):
        _record_ghl_writeback_failure(db, current_user, result, writeback)
    _transition_queue_state(result, request.state, current_user.id, request.reason)
    _audit(db, current_user, result.id, "hot_lead_state_changed", {
        "contact_id": result.contact_id,
        "actor_id": str(current_user.id),
        "from": previous_state,
        "to": request.state,
        "reason": request.reason,
        "ghl_writeback": writeback,
    })
    return {
        "status": result.queue_status,
        "result_id": str(result.id),
        "ghl_writeback": writeback,
        "warning": None if writeback.get("success") else "Queue state was saved in ENY, but GHL synchronization failed.",
    }


@router.post("/hot-leads/{result_id}/follow-up", dependencies=[Depends(require_permission("leads:write"))])
async def follow_up_hot_lead(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Notify the internal Sales & Enrollment queue before a human contacts the lead."""
    result = (
        db.query(BatchExecutionResult)
        .filter(BatchExecutionResult.id == result_id)
        .with_for_update()
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Hot lead not found")
    if not result.assigned_user_id or str(result.assigned_user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Claim the lead before triggering follow-up")
    previous_state = result.queue_status
    if previous_state != "assigned":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Follow-up can only be triggered before the lead has been contacted",
        )
    if result.follow_up_status in {"triggering", "tagged", "team_notified"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sales & Enrollment has already been notified for this lead",
        )
    if result.follow_up_status == "failed":
        latest_failure = db.query(OperationalAlert).filter(
            OperationalAlert.result_id == result.id,
            OperationalAlert.alert_type == "follow_up_tag_failure",
            OperationalAlert.source == "ghl",
        ).order_by(OperationalAlert.created_at.desc()).first()
        if not latest_failure or latest_failure.status != "acknowledged":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Review and acknowledge the workflow failure before retrying",
            )

    result.follow_up_status = "triggering"
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=result.id,
        event_type="follow_up_attempt_started",
        details={"contact_id": result.contact_id, "action": "notify_sales_enrollment"},
    ))
    db.commit()

    now = datetime.now(timezone.utc)
    result.follow_up_status = "team_notified"
    result.lifecycle_stage = "queued"
    result.lifecycle_updated_at = now
    result.notification_status = "sent"
    result.notification_error = None
    result.notification_sent_at = now
    team_alert = OperationalAlert(
        alert_type="sales_team_notification",
        source="sales_operations",
        severity="warning",
        message="An assigned hot lead is ready for manual outreach.",
        result_id=result.id,
        details={
            "contact_id": result.contact_id,
            "assigned_user_id": str(current_user.id),
            "score": result.score,
            "source": result.source,
            "recipient": "Sales & Enrollment team UI",
        },
    )
    db.add(team_alert)
    db.commit()

    tag_success = await ghl_service.tag_contact(str(result.contact_id), ["eny-follow-up-queued"])
    if not tag_success:
        result.follow_up_status = "failed"
        team_alert.message = "A hot lead needs manual outreach; GHL follow-up tag synchronization failed."
        team_alert.details = {**(team_alert.details or {}), "ghl_tag_written": False}
        _create_operational_alert(
            db,
            alert_type="follow_up_tag_failure",
            source="ghl",
            message="The team notification was recorded, but the GHL follow-up tag could not be written.",
            result_id=result.id,
            details={"contact_id": result.contact_id, "action": "notify_sales_enrollment"},
        )
        db.add(EnrollmentAudit(
            user_id=current_user.id,
            result_id=result.id,
            event_type="follow_up_tag_failed",
            details={"contact_id": result.contact_id, "tag": "eny-follow-up-queued"},
        ))
        db.commit()
    else:
        team_alert.details = {**(team_alert.details or {}), "ghl_tag_written": True}
        db.add(EnrollmentAudit(
            user_id=current_user.id,
            result_id=result.id,
            event_type="sales_team_notified",
            details={
                "contact_id": result.contact_id,
                "notification_channel": "sales_enrollment_ui",
                "lead_contacted": False,
                "ghl_tag_written": True,
            },
        ))

    chat_text = (
        "CRITICAL: Sales & Enrollment could not apply the GHL follow-up tag for an assigned hot lead."
        if not tag_success
        else "Sales & Enrollment: an assigned hot lead is ready for manual outreach."
    )
    chat_text += (
        f"\nScore: {result.score if result.score is not None else 'unknown'}"
        f"\nSource: {result.source or 'unknown'}"
        "\nOpen the ENY OS Sales & Enrollment alert inbox for the lead and audit details."
    )
    try:
        chat_delivery = await google_chat_service.send_message(chat_text)
    except httpx.HTTPError:
        logger.warning("Google Chat notification delivery failed for operational alert %s", team_alert.id)
        chat_delivery = {"status": "failed", "error": "Google Chat webhook delivery failed"}
        _create_operational_alert(
            db,
            alert_type="google_chat_delivery_failure",
            source="google_chat",
            severity="critical",
            message="Sales & Enrollment alert could not be delivered to Google Chat.",
            result_id=result.id,
            details={"related_alert_id": str(team_alert.id)},
        )

    team_alert.details = {
        **(team_alert.details or {}),
        "google_chat": chat_delivery,
        "lead_contacted": False,
    }
    result.last_action_at = now
    if tag_success:
        _audit(db, current_user, result.id, "follow_up_triggered", {
            "contact_id": result.contact_id,
            "from": previous_state,
            "to": result.queue_status,
            "notification_channel": "sales_enrollment_ui",
            "google_chat_status": chat_delivery["status"],
            "ghl_tag_written": True,
        })
    else:
        db.commit()

    if not tag_success:
        chat_note = (
            " Google Chat notification was sent."
            if chat_delivery["status"] == "sent"
            else f" Google Chat status: {chat_delivery['status']}."
        )
        raise HTTPException(
            status_code=502,
            detail=(
                "Sales & Enrollment was notified in the platform, but GHL tag synchronization failed."
                + chat_note
            ),
        )

    warning = None
    if chat_delivery["status"] != "sent":
        warning = (
            "The platform alert and GHL tag succeeded, but Google Chat "
            f"delivery status is {chat_delivery['status']}."
        )
    return {
        "status": result.follow_up_status,
        "queue_status": result.queue_status,
        "message": "Sales & Enrollment was notified in the platform. No email or text was sent to the lead.",
        "lead_contacted": False,
        "google_chat": chat_delivery,
        "warning": warning,
    }

@router.get("/pipeline", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_pipeline(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get enrollment pipeline data.
    Requires leads:read permission.
    """
    try:
        pipeline = await ghl_service.get_pipeline_data(include_inventory=True)
        opportunities = pipeline.get("opportunities", [])
        stages = pipeline.get("stages", [])
        pipeline_data = {
            "totalLeads": pipeline.get("total_leads", 0),
            "conversionRate": round(float(pipeline.get("conversion_rate", 0)) * 100, 2),
            "revenueForecast": pipeline.get("revenue_forecast", 0),
            "atRiskDeals": pipeline.get("at_risk_deals", 0),
        }
        return {
            "pipeline": pipeline_data,
            "stages": stages,
            "opportunities": opportunities,
            "pipelines": pipeline.get("pipelines", []),
            "status": pipeline.get("status", "error"),
            "pipeline_catalog_status": pipeline.get("pipeline_catalog_status", "error"),
            "max_pages_reached": pipeline.get("max_pages_reached", False),
        }
    except Exception as e:
        logger.error(f"Error fetching enrollment pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pipeline: {str(e)}"
        )


@router.get("/quality", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_quality(
    current_user: Any = Depends(get_current_user),
):
    """Return read-only GHL normalization and deduplication findings."""
    contacts, inventory = await ghl_service.get_all_contacts()
    return {
        "quality": ghl_service.build_contact_quality_report(contacts),
        "crm": inventory,
    }


@router.get("/adoption-policy", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_adoption_policy(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Return the shared Sales & Enrollment process policy and weekly review data."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = db.query(BatchExecutionResult).filter(BatchExecutionResult.created_at >= since).all()
    audits = db.query(EnrollmentAudit).filter(EnrollmentAudit.created_at >= since).all()
    lifecycle_counts: dict[str, int] = {}
    for row in rows:
        stage = getattr(row, "lifecycle_stage", "not_started")
        lifecycle_counts[stage] = lifecycle_counts.get(stage, 0) + 1
    return {
        "policy": OPERATING_POLICY,
        "review_window": {"days": 7, "since": since.isoformat(), "generated_at": datetime.now(timezone.utc).isoformat()},
        "weekly_review": {
            "results_created": len(rows),
            "audit_events": len(audits),
            "lifecycle_counts": lifecycle_counts,
            "closed_or_enrolled": len([row for row in rows if getattr(row, "queue_status", "") == "closed" or getattr(row, "lifecycle_stage", "") == "enrolled"]),
            "open_escalations": len([row for row in rows if getattr(row, "status", "") == "escalated"]),
            "stale_active_work": len([row for row in rows if getattr(row, "queue_status", "new") in {"new", "assigned", "contacted"} and _hours_since(getattr(row, "last_action_at", None) or getattr(row, "created_at", None)) > 24]),
        },
    }


@router.get("/reporting", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_reporting(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Return performance reporting for the Sales & Enrollment operating review."""
    rows = db.query(BatchExecutionResult).all()
    audits = db.query(EnrollmentAudit).all()
    source_rows: dict[str, list[Any]] = {}
    for row in rows:
        source_rows.setdefault(getattr(row, "source", None) or "unknown", []).append(row)

    def count_state(items: list[Any], states: set[str]) -> int:
        return len([row for row in items if getattr(row, "queue_status", "new") in states])

    hot_rows = [row for row in rows if getattr(row, "category", "") == "hot"]
    hot_aging = {
        "under_1_day": len([row for row in hot_rows if _hours_since(getattr(row, "last_action_at", None) or getattr(row, "created_at", None)) < 24]),
        "one_to_three_days": len([row for row in hot_rows if 24 <= _hours_since(getattr(row, "last_action_at", None) or getattr(row, "created_at", None)) < 72]),
        "over_3_days": len([row for row in hot_rows if _hours_since(getattr(row, "last_action_at", None) or getattr(row, "created_at", None)) >= 72]),
    }
    lifecycle_counts: dict[str, int] = {}
    for row in rows:
        stage = getattr(row, "lifecycle_stage", "not_started")
        lifecycle_counts[stage] = lifecycle_counts.get(stage, 0) + 1
    audit_types = [str(getattr(event, "event_type", "")) for event in audits]
    pipeline = await ghl_service.get_pipeline_data()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "leads_by_source": {
            source: {
                "total": len(items),
                "hot": len([row for row in items if getattr(row, "category", "") == "hot"]),
                "contacted": count_state(items, {"contacted", "qualified", "closed"}),
                "qualified": count_state(items, {"qualified", "closed"}),
                "closed": count_state(items, {"closed"}),
                "conversion_percent": round(count_state(items, {"closed"}) / len(items) * 100) if items else 0,
            }
            for source, items in sorted(source_rows.items())
        },
        "conversion_funnel": {
            "new": count_state(rows, {"new"}),
            "assigned": count_state(rows, {"assigned", "contacted", "qualified", "closed"}),
            "contacted": count_state(rows, {"contacted", "qualified", "closed"}),
            "qualified": count_state(rows, {"qualified", "closed"}),
            "closed": count_state(rows, {"closed"}),
            "enrolled": lifecycle_counts.get("enrolled", 0),
        },
        "hot_lead_aging": hot_aging,
        "follow_up_completion": {
            "queued": lifecycle_counts.get("queued", 0),
            "outreach_sent": lifecycle_counts.get("outreach_sent", 0),
            "responded": lifecycle_counts.get("responded", 0),
            "booked": lifecycle_counts.get("booked", 0),
            "completed_or_outcome": lifecycle_counts.get("enrolled", 0) + lifecycle_counts.get("lost", 0),
            "failed": lifecycle_counts.get("failed", 0),
        },
        "blocked_queue": {
            "held": len([row for row in rows if getattr(row, "status", "") == "held"]),
            "escalated": len([row for row in rows if getattr(row, "status", "") == "escalated"]),
            "workflow_failures": len([row for row in rows if getattr(row, "error", None) or getattr(row, "follow_up_status", "") == "failed"]),
            "data_quality": len([row for row in rows if not getattr(row, "email", None) and not getattr(row, "phone", None)]),
        },
        "exceptions": {
            "reassignments": len([event for event in audit_types if "assign" in event or "claim" in event]),
            "recovery_decisions": len([event for event in audit_types if "recovery" in event or "retry" in event]),
            "lifecycle_changes": len([event for event in audit_types if "lifecycle" in event]),
            "failed_events": len([event for event in audit_types if "failed" in event or "error" in event]),
        },
        "ghl_pipeline": {
            "conversion_rate": round(float(pipeline.get("conversion_rate", 0)) * 100, 2),
            "revenue_forecast": pipeline.get("revenue_forecast", 0),
            "stages": pipeline.get("stages", []),
        },
    }


@router.get("/alerts", dependencies=[Depends(require_permission("leads:read"))])
async def get_enrollment_alerts(
    limit: int = Query(50, ge=1, le=200),
    include_acknowledged: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Return persistent hard-failure alerts for the Sales & Enrollment team."""
    query = db.query(OperationalAlert).filter(OperationalAlert.team == "sales_enrollment")
    if not include_acknowledged:
        query = query.filter(OperationalAlert.status == "open")
    alerts = query.order_by(OperationalAlert.created_at.desc()).limit(limit).all()
    return {
        "alerts": [
            {
                "id": str(alert.id),
                "type": alert.alert_type,
                "severity": alert.severity,
                "source": alert.source,
                "message": alert.message,
                "result_id": str(alert.result_id) if alert.result_id else None,
                "status": alert.status,
                "details": alert.details,
                "created_at": _serialize_datetime(alert.created_at),
                "acknowledged_at": _serialize_datetime(alert.acknowledged_at),
            }
            for alert in alerts
        ],
        "open_count": db.query(OperationalAlert).filter(
            OperationalAlert.team == "sales_enrollment",
            OperationalAlert.status == "open",
        ).count(),
    }


@router.get("/alerts/inbox", dependencies=[Depends(require_permission("sales:alerts:read"))])
async def get_sales_alert_inbox(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """List shared Sales & Enrollment alerts with this user's read/dismiss state."""
    state_join = and_(
        OperationalAlertUserState.alert_id == OperationalAlert.id,
        OperationalAlertUserState.user_id == current_user.id,
    )
    visible_query = (
        db.query(OperationalAlert)
        .outerjoin(OperationalAlertUserState, state_join)
        .filter(OperationalAlert.team == "sales_enrollment")
        .filter(or_(
            OperationalAlertUserState.user_id.is_(None),
            OperationalAlertUserState.dismissed_at.is_(None),
        ))
    )
    rows = (
        db.query(OperationalAlert, OperationalAlertUserState)
        .outerjoin(OperationalAlertUserState, state_join)
        .filter(OperationalAlert.team == "sales_enrollment")
        .filter(or_(
            OperationalAlertUserState.user_id.is_(None),
            OperationalAlertUserState.dismissed_at.is_(None),
        ))
        .order_by(OperationalAlert.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "alerts": [
            {
                "id": str(alert.id),
                "type": alert.alert_type,
                "severity": alert.severity,
                "source": alert.source,
                "message": alert.message,
                "result_id": str(alert.result_id) if alert.result_id else None,
                "status": alert.status,
                "details": alert.details,
                "created_at": _serialize_datetime(alert.created_at),
                "read_at": _serialize_datetime(user_state.read_at) if user_state else None,
                "is_read": bool(user_state and user_state.read_at),
            }
            for alert, user_state in rows
        ],
        "total_count": visible_query.count(),
        "unread_count": (
            db.query(OperationalAlert)
            .outerjoin(OperationalAlertUserState, state_join)
            .filter(OperationalAlert.team == "sales_enrollment")
            .filter(or_(
                OperationalAlertUserState.user_id.is_(None),
                OperationalAlertUserState.dismissed_at.is_(None),
            ))
            .filter(or_(
                OperationalAlertUserState.user_id.is_(None),
                OperationalAlertUserState.read_at.is_(None),
            ))
            .count()
        ),
        "critical_count": visible_query.filter(
            OperationalAlert.severity == "critical",
        ).count(),
    }


@router.post("/alerts/{alert_id}/read", dependencies=[Depends(require_permission("sales:alerts:read"))])
async def mark_sales_alert_read(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Record that the current user read a shared alert."""
    alert = db.query(OperationalAlert).filter(
        OperationalAlert.id == alert_id,
        OperationalAlert.team == "sales_enrollment",
    ).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operational alert not found")

    now = datetime.now(timezone.utc)
    db.execute(
        pg_insert(OperationalAlertUserState)
        .values(alert_id=alert.id, user_id=current_user.id, read_at=now)
        .on_conflict_do_update(
            index_elements=[
                OperationalAlertUserState.alert_id,
                OperationalAlertUserState.user_id,
            ],
            set_={"read_at": now},
        )
    )
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=alert.result_id,
        event_type="operational_alert_read",
        details={"alert_id": str(alert.id), "alert_type": alert.alert_type},
    ))
    db.commit()
    return {"id": str(alert.id), "is_read": True, "read_at": _serialize_datetime(now)}


@router.delete("/alerts/{alert_id}/inbox", dependencies=[Depends(require_permission("sales:alerts:manage"))])
async def dismiss_sales_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Dismiss an alert from the current user's inbox without deleting the shared record."""
    alert = db.query(OperationalAlert).filter(
        OperationalAlert.id == alert_id,
        OperationalAlert.team == "sales_enrollment",
    ).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operational alert not found")

    now = datetime.now(timezone.utc)
    db.execute(
        pg_insert(OperationalAlertUserState)
        .values(alert_id=alert.id, user_id=current_user.id, dismissed_at=now)
        .on_conflict_do_update(
            index_elements=[
                OperationalAlertUserState.alert_id,
                OperationalAlertUserState.user_id,
            ],
            set_={"dismissed_at": now},
        )
    )
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=alert.result_id,
        event_type="operational_alert_dismissed",
        details={"alert_id": str(alert.id), "alert_type": alert.alert_type},
    ))
    db.commit()
    return {"id": str(alert.id), "dismissed": True}


@router.post("/alerts/ai-summary", dependencies=[Depends(require_permission("sales:alerts:read"))])
async def summarize_sales_alerts(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Ask Claude for a bounded, count-aware summary of recent platform alerts."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_query = db.query(OperationalAlert).filter(
        OperationalAlert.team == "sales_enrollment",
        OperationalAlert.created_at >= since,
    )
    total_count = recent_query.count()
    critical_count = recent_query.filter(OperationalAlert.severity == "critical").count()
    join_condition = and_(
        OperationalAlertUserState.alert_id == OperationalAlert.id,
        OperationalAlertUserState.user_id == current_user.id,
    )
    unread_count = (
        db.query(OperationalAlert)
        .outerjoin(OperationalAlertUserState, join_condition)
        .filter(
            OperationalAlert.team == "sales_enrollment",
            OperationalAlert.created_at >= since,
        )
        .filter(or_(
            OperationalAlertUserState.user_id.is_(None),
            OperationalAlertUserState.dismissed_at.is_(None),
        ))
        .filter(or_(
            OperationalAlertUserState.user_id.is_(None),
            OperationalAlertUserState.read_at.is_(None),
        ))
        .count()
    )
    recent_alerts = recent_query.order_by(OperationalAlert.created_at.desc()).limit(50).all()
    critical_alerts = [
        {
            "type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message[:500],
            "created_at": _serialize_datetime(alert.created_at),
        }
        for alert in recent_alerts
        if alert.severity == "critical"
    ]
    if total_count == 0:
        return {
            "summary": "No Sales & Enrollment alerts were recorded in the last 24 hours.",
            "counts": {"total_24h": 0, "unread": 0, "critical_24h": 0},
            "generated_at": _serialize_datetime(datetime.now(timezone.utc)),
        }

    context = {
        "counts": {
            "total_24h": total_count,
            "unread": unread_count,
            "critical_24h": critical_count,
        },
        "critical_alerts_in_latest_50": critical_alerts,
        "latest_alerts": [
            {
                "type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message[:500],
                "created_at": _serialize_datetime(alert.created_at),
            }
            for alert in recent_alerts
        ],
    }
    try:
        summary = await ClaudeService().summarize_operational_alerts(context)
    except ValueError as exc:
        logger.warning("Claude alert summary unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claude alert summaries are not configured or returned an invalid response.",
        ) from exc
    except anthropic.APIError as exc:
        logger.warning("Claude alert summary request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Claude could not summarize Sales & Enrollment alerts right now.",
        ) from exc
    return {
        "summary": summary,
        "counts": context["counts"],
        "generated_at": _serialize_datetime(datetime.now(timezone.utc)),
    }


@router.patch("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_permission("leads:write"))])
async def acknowledge_enrollment_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Acknowledge a hard failure after an owner has accepted the operational action."""
    alert = db.query(OperationalAlert).filter(
        OperationalAlert.id == alert_id,
        OperationalAlert.team == "sales_enrollment",
    ).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operational alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = current_user.id
    db.add(EnrollmentAudit(
        user_id=current_user.id,
        result_id=alert.result_id,
        event_type="operational_alert_acknowledged",
        details={"alert_id": str(alert.id), "alert_type": alert.alert_type, "source": alert.source},
    ))
    db.commit()
    return {"id": str(alert.id), "status": alert.status, "acknowledged_at": _serialize_datetime(alert.acknowledged_at)}