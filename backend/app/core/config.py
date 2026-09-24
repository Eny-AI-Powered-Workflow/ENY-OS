from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional, Union
import json


def parse_origins(raw: str) -> List[str]:
    """Accept either a comma-separated list or a JSON array of allowed origins."""
    if not raw:
        return []
    value = raw.strip()
    if value.startswith("["):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(entry).strip() for entry in parsed if str(entry).strip()]
    return [entry.strip() for entry in value.split(",") if entry.strip()]


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ENY Consulting Platform"

    # CORS Settings
    BACKEND_CORS_ORIGINS: str = "https://eny-os.vercel.app,https://eny-os.onrender.com"
    # Documented alias (see backend/.env.example). Entries here are merged with
    # BACKEND_CORS_ORIGINS instead of being silently ignored.
    ALLOWED_ORIGINS: str = ""
    # Optional regex for ephemeral preview deployments, e.g. r"https://eny-.*\.vercel\.app".
    CORS_ORIGIN_REGEX: str = ""

    # Security Settings
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_JWT_SECRET: str = Field(..., env="SUPABASE_JWT_SECRET")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_ANON_KEY: str = Field(..., env="SUPABASE_ANON_KEY")
    SUPABASE_JWT_AUDIENCE: str = Field("authenticated", env="SUPABASE_JWT_AUDIENCE")

    # Database Settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # External Service Settings
    GHL_BASE_URL: str = Field("https://services.leadconnectorhq.com", env="GHL_BASE_URL")
    GHL_API_KEY: str = Field("", env="GHL_API_KEY")
    GHL_LOCATION_ID: str = Field("", env="GHL_LOCATION_ID")
    GHL_PRIVATE_TOKEN: str = Field("", env="GHL_PRIVATE_TOKEN")
    GHL_SALES_SCORE_FIELD_ID: str = Field("caiccVdZ41m5BMyWMH57", env="GHL_SALES_SCORE_FIELD_ID")
    GHL_SCORE_CATEGORY_FIELD_ID: str = Field("CiowYO5hnAmwWKCp7vAO", env="GHL_SCORE_CATEGORY_FIELD_ID")
    GHL_ENROLLMENT_STATUS_FIELD_ID: str = Field("", env="GHL_ENROLLMENT_STATUS_FIELD_ID")
    GHL_ENROLLMENT_OWNER_FIELD_ID: str = Field("", env="GHL_ENROLLMENT_OWNER_FIELD_ID")
    GHL_ENROLLMENT_LIFECYCLE_FIELD_ID: str = Field("", env="GHL_ENROLLMENT_LIFECYCLE_FIELD_ID")
    GHL_CONTACT_MAX_PAGES: int = Field(20, env="GHL_CONTACT_MAX_PAGES")
    BATCH_MAX_RETRIES: int = Field(3, env="BATCH_MAX_RETRIES")
    BATCH_RETRY_BACKOFF_SECONDS: int = Field(60, env="BATCH_RETRY_BACKOFF_SECONDS")

    N8N_BASE_URL: str = Field("http://localhost:5678", env="N8N_BASE_URL")
    N8N_API_KEY: str = Field("", env="N8N_API_KEY")
    N8N_WEBHOOK_TOKEN: str = Field("", env="N8N_WEBHOOK_TOKEN")
    N8N_MOCK_MODE: bool = Field(False, env="N8N_MOCK_MODE")

    ANTHROPIC_API_KEY: str = Field(..., env="ANTHROPIC_API_KEY")
    CLAUDE_MODEL: str = Field("claude-3-opus-20240229", env="CLAUDE_MODEL")
    OPENAI_API_KEY: str = Field("", env="OPENAI_API_KEY")
    EMBEDDING_MODEL: str = Field("text-embedding-3-small", env="EMBEDDING_MODEL")

    # OpenAI embeddings are rate limited per account. Large SOP uploads are
    # batched to reduce pressure, but HTTP 429s must fail fast in a live product
    # instead of blocking the request thread with a long retry loop.
    EMBEDDING_BATCH_SIZE: int = Field(32, env="EMBEDDING_BATCH_SIZE")
    EMBEDDING_MAX_RETRIES: int = Field(0, env="EMBEDDING_MAX_RETRIES")
    EMBEDDING_RETRY_BASE_SECONDS: float = Field(1.0, env="EMBEDDING_RETRY_BASE_SECONDS")
    EMBEDDING_RETRY_MAX_SECONDS: float = Field(20.0, env="EMBEDDING_RETRY_MAX_SECONDS")
    EMBEDDING_TIMEOUT_SECONDS: float = Field(60.0, env="EMBEDDING_TIMEOUT_SECONDS")
    # Upper bound on how many chunks a single SOP upload may produce.
    KNOWLEDGE_MAX_CHUNKS: int = Field(400, env="KNOWLEDGE_MAX_CHUNKS")

    # Optional APIs
    APOLLO_API_KEY: str = Field("", env="APOLLO_API_KEY")
    PERPLEXITY_API_KEY: str = Field("", env="PERPLEXITY_API_KEY")

    # Server Settings
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")

    @property
    def cors_origins(self) -> List[str]:
        """Union of BACKEND_CORS_ORIGINS and the documented ALLOWED_ORIGINS alias."""
        merged: List[str] = []
        for origin in parse_origins(self.BACKEND_CORS_ORIGINS) + parse_origins(self.ALLOWED_ORIGINS):
            if origin not in merged:
                merged.append(origin)
        return merged

    @property
    def cors_origin_regex(self) -> Optional[str]:
        """Optional pattern for preview deployments; disabled when unset."""
        return self.CORS_ORIGIN_REGEX.strip() or None

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'


settings = Settings()
