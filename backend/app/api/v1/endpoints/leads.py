# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/leads.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.api.deps import require_permission
from app.services.ghl_service import ghl_service

router = APIRouter()


@router.get("", dependencies=[Depends(require_permission("leads:read"))])
async def get_leads(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    cursor_id: Optional[str] = Query(None, max_length=200),
    cursor_after: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db)
):
    """
    Get a list of leads/contacts from GHL.
    Requires leads:read permission.
    """
    try:
        if cursor_id or cursor_after:
            leads, next_cursor = await ghl_service.get_contacts_page(
                limit=limit,
                cursor_id=cursor_id,
                cursor_after=cursor_after,
            )
        elif offset:
            leads, next_cursor = await ghl_service.get_contacts_offset_page(limit=limit, offset=offset)
        else:
            leads, next_cursor = await ghl_service.get_contacts_page(limit=limit)
        return {
            "leads": leads,
            "total": len(leads),
            "limit": limit,
            "offset": offset,
            "has_more": next_cursor is not None,
            "next_cursor": next_cursor,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve leads: {str(e)}"
        )


@router.get("/{lead_id}", dependencies=[Depends(require_permission("leads:read"))])
async def get_lead(
    lead_id: str = Path(..., description="The ID of the lead to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Get a specific lead by ID from GHL.
    Requires leads:read permission.
    """
    try:
        lead = await ghl_service.get_contact(lead_id)
        if not lead:
            raise HTTPException(
                status_code=404,
                detail=f"Lead with ID {lead_id} not found"
            )
        return lead
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve lead: {str(e)}"
        )


@router.post("/{lead_id}/tags", dependencies=[Depends(require_permission("leads:write"))])
async def add_tags_to_lead(
    lead_id: str = Path(..., description="The ID of the lead to tag"),
    tags: List[str] = ...,
    db: Session = Depends(get_db)
):
    """
    Add tags to a lead in GHL.
    Requires leads:write permission.
    """
    try:
        success = await ghl_service.tag_contact(lead_id, tags)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to add tags to lead {lead_id}"
            )
        return {
            "status": "success",
            "message": f"Tags {tags} added to lead {lead_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add tags to lead: {str(e)}"
        )