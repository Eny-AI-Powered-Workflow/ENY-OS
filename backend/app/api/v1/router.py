# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, leads, pipeline, agents

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])