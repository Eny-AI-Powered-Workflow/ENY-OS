# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/endpoints/student-success.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from app.api.deps import require_permission
from app.core.security import get_current_user
from app.db.session = get_db
from sqlalchemy.orm = Session
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/metrics", dependencies=[Depends(require_permission("students:read"))])
async def get_student_success_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get student success dashboard metrics.
    Requires students:read permission.
    """
    try:
        metrics = {
            "totalStudents": 892,
            "atRiskStudents": 67,
            "graduationRate": 82.3,
            "interventionsToday": 12
        }
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching student success metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )

@router.get("/students", dependencies=[Depends(require_permission("students:read"))])
async def get_student_list(
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    risk: Optional[str] = None
Visibility: Visible to you and the agent
):
    """
    Get student list.
    Requires students:read permission.
    """
    try:
        # Mock data
        students = []
        for i in range(min(limit, 10)):
            status = "at-risk" if i % 4 == 0 else "on-track"
            students.append({
                "id": f"student_{i+1}",
                "firstName": f"Student{i+1}",
                "lastName": f"Lastname{i+1}",
                "email": f"student{i+1}@example.com",
                "studentId": f"STU{1000+i+1}",
                "status": status,
                "interventionsToday": i % 3
            })
        return {"students": students}
    except Exception as e:
        logger.error(f"Error fetching student list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch students: {str(e)}"
        )

@router.get("/progress", dependencies=[Depends(require_permission("students:read"))])
async def get_student_progress(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get student progress data.
    Requires students:read permission.
    """
    try:
        progress_data = {
            "graduationRate": 82.3,
            "averageGpa": 3.2,
            "retentionRate": 88.7,
            "collegeAcceptanceRate": 76.5
        }
        interventions = [
            {"id": "1", "title": "Tutoring Session", "description": "Math tutoring for struggling students", "timeAgo": "1 hour ago"},
            {"id": "2", "title": "Parent Meeting", "description": "Discussion about academic progress", "timeAgo": "3 hours ago"},
            {"id": "3", "title": "Study Group", "description": "Weekly study group meeting", "timeAgo": "5 hours ago"}
        ]
        return {"progress": progress_data, "recentInterventions": interventions}
    except Exception as e:
        logger.error(f"Error fetching student progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch progress: {str(e)}"
        )