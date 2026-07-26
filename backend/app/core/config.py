# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Union
import json


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ENY Consulting Platform"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = []

    # Security Settings
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_JWT_SECRET: str = Field(..., env="SUPABASE_JWT_SECRET")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_JWT_AUDIENCE: str = Field("authenticated", env="SUPABASE_JWT_AUDIENCE")

    # Database Settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # External Service Settings
    GHL_BASE_URL: str = Field("https://services.leadconnectorhq.com", env="GHL_BASE_URL")
    GHL_API_KEY: str = Field("", env="GHL_API_KEY")
    GHL_LOCATION_ID: str = Field("", env="GHL_LOCATION_ID")
    GHL_PRIVATE_TOKEN: str = Field("", env="GHL_PRIVATE_TOKEN")

    N8N_BASE_URL: str = Field("http://localhost:5678", env="N8N_BASE_URL")
    N8N_API_KEY: str = Field("", env="N8N_API_KEY")

    ANTHROPIC_API_KEY: str = Field(..., env="ANTHROPIC_API_KEY")
    CLAUDE_MODEL: str = Field("claude-3-opus-20240229", env="CLAUDE_MODEL")

    # Optional APIs
    APOLLO_API_KEY: str = Field("", env="APOLLO_API_KEY")
    PERPLEXITY_API_KEY: str = Field("", env="PERPLEXITY_API_KEY")

    # Server Settings
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'


settings = Settings()