# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/core/config.py
from pydantic import BaseSettings, Field
from typing import List, Union
import json


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ENY Consulting Platform"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = []

    # Security Settings
    SUPABASE_JWT_SECRET: str = Field(..., env="SUPABASE_JWT_SECRET")
    SUPABASE_JWT_AUDIENCE: str = Field("authenticated", env="SUPABASE_JWT_AUDIENCE")

    # Database Settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # External Service Settings
    GHL_BASE_URL: str = Field("https://services.leadconnectorhq.com", env="GHL_BASE_URL")
    GHL_PRIVATE_TOKEN: str = Field("", env="GHL_PRIVATE_TOKEN")
    GHL_LOCATION_ID: str = Field("", env="GHL_LOCATION_ID")

    N8N_BASE_URL: str = Field("http://localhost:5678", env="N8N_BASE_URL")
    N8N_API_KEY: str = Field("", env="N8N_API_KEY")

    ANTHROPIC_API_KEY: str = Field(..., env="ANTHROPIC_API_KEY")
    CLAUDE_MODEL: str = Field("claude-3-opus-20240229", env="CLAUDE_MODEL")

    # Server Settings
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'


settings = Settings()