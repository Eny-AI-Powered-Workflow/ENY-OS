# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/marketing.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session = get_db
from sqlalchemy.orm = Session
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/metrics", dependencies=[Depends(require_permission("leads:read"))])
async def get_marketing_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get marketing dashboard metrics.
    Requires leads:read permission.
    """
    try:
        metrics = {
            "totalLeads": 3420,
            "leadsThisMonth": 425,
            "conversionRate": 12.8,
            "roi": 3.4
        }
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching marketing metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )

@router.get("/analytics", dependencies=[Depends(require_permission("leads:read"))])
async def get_marketing_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get marketing analytics.
    Requires leads:read permission.
    """
    try:
        campaigns = [
            {
                "id": "1",
                "name": "Q3 Social Media Campaign",
                "description": "Facebook and Instagram lead generation campaign",
                "impressions": 125000,
                "clicks": 3200,
                "ctr": 2.56,
                "conversions": 185,
                "conversionRate": 5.78,
                "cost": 8500,
                "roi": 4.2
            },
            {
                "id": "2",
                "name": "Email Newsletter Series",
                "description": "Monthly educational newsletter",
                "impressions": 89000,
                "clicks": 4500,
                "ctr": 5.06,
                "conversions": 210,
                "conversionRate": 4.67,
                "cost": 3200,
                "roi": 8.9
            }
        ]
        return {"campaigns": campaigns}
    except Exception as e:
        logger.error(f"Error fetching marketing analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analytics: {str(e)}"
        )