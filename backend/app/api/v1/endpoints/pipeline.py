# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/pipeline.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_permission
from app.services.ghl_service import ghl_service

router = APIRouter()


@router.get("/")
async def get_pipeline(
    db: Session = Depends(get_db)
):
    """
    Get pipeline/opportunities data from GHL.
    Requires pipeline:read permission.
    """
    try:
        pipeline_data = await ghl_service.get_pipeline_data()
        return pipeline_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve pipeline data: {str(e)}"
        )


@router.get("/forecast")
async def get_revenue_forecast(
    db: Session = Depends(get_db)
):
    """
    Get revenue forecast from pipeline data.
    Requires pipeline:read permission.
    """
    try:
        pipeline_data = await ghl_service.get_pipeline_data()
        return {
            "forecast": pipeline_data.get("revenue_forecast", 0),
            "currency": "USD",
            "period": "monthly",
            "confidence": "medium",
            "assumptions": [
                "Based on current pipeline and historical conversion rates",
                "Assumes no major market changes",
                "Includes weighted probability of deal closure"
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate revenue forecast: {str(e)}"
        )