# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/marketing.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.services.ghl_service import ghl_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/metrics", dependencies=[Depends(require_permission("marketing:analytics"))])
async def get_marketing_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get marketing dashboard metrics.
    Requires marketing:analytics permission.
    """
    try:
        contacts, _ = await ghl_service.get_all_contacts()
        pipeline = await ghl_service.get_pipeline_data()
        current_month = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m")
        metrics = {
            "totalLeads": len(contacts),
            "leadsThisMonth": sum(1 for contact in contacts if str(contact.get("dateAdded", "")).startswith(current_month)),
            "conversionRate": round(float(pipeline.get("conversion_rate", 0)) * 100, 2),
            "roi": None,
        }
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching marketing metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )

@router.get("/analytics", dependencies=[Depends(require_permission("marketing:analytics"))])
async def get_marketing_analytics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get marketing analytics.
    Requires marketing:analytics permission.
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