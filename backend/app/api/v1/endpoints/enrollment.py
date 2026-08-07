# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/enrollment.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

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
        metrics = {
            "totalLeads": 1542,
            "newLeadsToday": 23,
            "conversionRate": 18.5,
            "revenuePipeline": 425000
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
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get enrollment leads.
    Requires leads:read permission.
    """
    try:
        # Mock data
        leads = []
        for i in range(min(limit, 10)):  # Return up to 10 mock leads
            leads.append({
                "id": f"lead_{i+1}",
                "firstName": f"FirstName{i+1}",
                "lastName": f"LastName{i+1}",
                "email": f"lead{i+1}@example.com",
                "phone": f"555-000-{i+1:04d}",
                "score": 75 + (i * 2) % 25,
                "tags": ["hot"] if i % 3 == 0 else ["warm"] if i % 3 == 1 else ["follow-up"]
            })
        return {"leads": leads}
    except Exception as e:
        logger.error(f"Error fetching enrollment leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch leads: {str(e)}"
        )

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
        pipeline_data = {
            "totalLeads": 1542,
            "conversionRate": 18.5,
            "revenueForecast": 425000,
            "atRiskDeals": 45
        }
        stages = [
            {"id": "1", "name": "New Lead", "description": "Recently acquired leads", "count": 320, "percentage": 20.7, "color": "gray"},
            {"id": "2", "name": "Contacted", "description": "Initial contact made", "count": 280, "percentage": 18.2, "color": "blue"},
            {"id": "3", "name": "Qualified", "description": "Meets basic criteria", "count": 250, "percentage": 16.2, "color": "green"},
            {"id": "4", "name": "Proposal Sent", "description": "Proposal/quote sent", "count": 180, "percentage": 11.7, "color": "yellow"},
            {"id": "5", "name": "Negotiation", "description": "Price/terms negotiation", "count": 120, "percentage": 7.8, "color": "orange"},
            {"id": "6", "name": "Closed Won", "description": "Successfully converted", "count": 285, "percentage": 18.5, "color": "green"},
            {"id": "7", "name": "Closed Lost", "description": "Did not convert", "count": 307, "percentage": 19.9, "color": "red"}
        ]
        return {"pipeline": pipeline_data, "stages": stages}
    except Exception as e:
        logger.error(f"Error fetching enrollment pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pipeline: {str(e)}"
        )