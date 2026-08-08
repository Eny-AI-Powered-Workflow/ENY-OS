# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, leads, pipeline, agents, ceo, enrollment, student_success, marketing, operations, writer

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(ceo.router, prefix="/ceo", tags=["ceo"])
api_router.include_router(enrollment.router, prefix="/enrollment", tags=["enrollment"])
api_router.include_router(student_success.router, prefix="/student-success", tags=["student-success"])
api_router.include_router(marketing.router, prefix="/marketing", tags=["marketing"])
api_router.include_router(operations.router, prefix="/operations", tags=["operations"])
api_router.include_router(writer.router, prefix="/writer", tags=["writer"])