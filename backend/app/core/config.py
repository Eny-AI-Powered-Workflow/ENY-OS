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
    GHL_ENROLLMENT_STATUS_FIELD_ID: str = Field("OuRGORJLJYHMOXNlhAcH", env="GHL_ENROLLMENT_STATUS_FIELD_ID")
    GHL_MARKETING_FROM_EMAIL: str = Field("", env="GHL_MARKETING_FROM_EMAIL")
    GHL_MARKETING_FROM_NAME: str = Field("ENY Consulting", env="GHL_MARKETING_FROM_NAME")
    GHL_MARKETING_LOCATION_ID: str = Field("", env="GHL_MARKETING_LOCATION_ID")
    GHL_MARKETING_CONSENT_FIELD_ID: str = Field("", env="GHL_MARKETING_CONSENT_FIELD_ID")
    BUFFER_ACCESS_TOKEN: str = Field("", env="BUFFER_ACCESS_TOKEN")
    BUFFER_PROFILE_IDS: str = Field("", env="BUFFER_PROFILE_IDS")
    GSC_SERVICE_ACCOUNT_JSON: str = Field("", env="GSC_SERVICE_ACCOUNT_JSON")
    GA4_PROPERTY_ID: str = Field("", env="GA4_PROPERTY_ID")
    GA4_SERVICE_ACCOUNT_JSON: str = Field("", env="GA4_SERVICE_ACCOUNT_JSON")
    AHREFS_API_KEY: str = Field("", env="AHREFS_API_KEY")
    SEMRUSH_API_KEY: str = Field("", env="SEMRUSH_API_KEY")
    PAGESPEED_API_KEY: str = Field("", env="PAGESPEED_API_KEY")
    DATAFORSEO_LOGIN: str = Field("", env="DATAFORSEO_LOGIN")
    DATAFORSEO_PASSWORD: str = Field("", env="DATAFORSEO_PASSWORD")
    SERPAPI_API_KEY: str = Field("", env="SERPAPI_API_KEY")
    LINKEDIN_ACCESS_TOKEN: str = Field("", env="LINKEDIN_ACCESS_TOKEN")
    META_ACCESS_TOKEN: str = Field("", env="META_ACCESS_TOKEN")
    X_BEARER_TOKEN: str = Field("", env="X_BEARER_TOKEN")
    YOUTUBE_API_KEY: str = Field("", env="YOUTUBE_API_KEY")
    REDDIT_CLIENT_ID: str = Field("", env="REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: str = Field("", env="REDDIT_CLIENT_SECRET")
    SLACK_BOT_TOKEN: str = Field("", env="SLACK_BOT_TOKEN")
    SUPABASE_MARKETING_VIDEO_BUCKET: str = Field("marketing-video", env="SUPABASE_MARKETING_VIDEO_BUCKET")
    MARKETING_VIDEO_MAX_UPLOAD_MB: int = Field(250, env="MARKETING_VIDEO_MAX_UPLOAD_MB")
    FFMPEG_PATH: str = Field("ffmpeg", env="FFMPEG_PATH")
    CANVA_ACCESS_TOKEN: str = Field("", env="CANVA_ACCESS_TOKEN")
    CANVA_CLIENT_ID: str = Field("", env="CANVA_CLIENT_ID")
    CANVA_CLIENT_SECRET: str = Field("", env="CANVA_CLIENT_SECRET")
    MARKETING_APPROVAL_SLA_HOURS: int = Field(72, env="MARKETING_APPROVAL_SLA_HOURS")
    MARKETING_LOW_PERFORMANCE_DROP_PCT: float = Field(30.0, env="MARKETING_LOW_PERFORMANCE_DROP_PCT")
    MARKETING_UNSUBSCRIBE_ALERT_RATE: float = Field(2.0, env="MARKETING_UNSUBSCRIBE_ALERT_RATE")
    SUPABASE_DESIGN_ASSET_BUCKET: str = Field("design-assets", env="SUPABASE_DESIGN_ASSET_BUCKET")
    DESIGN_ASSET_MAX_UPLOAD_MB: int = Field(50, env="DESIGN_ASSET_MAX_UPLOAD_MB")
    CANVA_CLIENT_ID: str = Field("", env="CANVA_CLIENT_ID")
    CANVA_CLIENT_SECRET: str = Field("", env="CANVA_CLIENT_SECRET")
    CANVA_REDIRECT_URI: str = Field("", env="CANVA_REDIRECT_URI")
    CANVA_POST_CONNECT_REDIRECT: str = Field("http://localhost:3000/dashboard/designer", env="CANVA_POST_CONNECT_REDIRECT")
    CANVA_TOKEN_ENCRYPTION_KEY: str = Field("", env="CANVA_TOKEN_ENCRYPTION_KEY")
    CANVA_OAUTH_SCOPES: str = Field("brandtemplate:content:read design:content:write design:meta:read design:content:read", env="CANVA_OAUTH_SCOPES")
    WEBFLOW_ACCESS_TOKEN: str = Field("", env="WEBFLOW_ACCESS_TOKEN")
    WEBFLOW_SITE_ID: str = Field("", env="WEBFLOW_SITE_ID")
    WEBFLOW_CMS_COLLECTION_ID: str = Field("", env="WEBFLOW_CMS_COLLECTION_ID")
    WEBFLOW_PUBLIC_BASE_URL: str = Field("", env="WEBFLOW_PUBLIC_BASE_URL")
    WEBFLOW_PUBLISH_TO_SUBDOMAIN: bool = Field(False, env="WEBFLOW_PUBLISH_TO_SUBDOMAIN")
    GHL_CONTACT_MAX_PAGES: int = Field(20, env="GHL_CONTACT_MAX_PAGES")
    BATCH_MAX_RETRIES: int = Field(3, env="BATCH_MAX_RETRIES")
    BATCH_RETRY_BACKOFF_SECONDS: int = Field(60, env="BATCH_RETRY_BACKOFF_SECONDS")

    N8N_BASE_URL: str = Field("http://localhost:5678", env="N8N_BASE_URL")
    N8N_API_KEY: str = Field("", env="N8N_API_KEY")
    N8N_WEBHOOK_TOKEN: str = Field("", env="N8N_WEBHOOK_TOKEN")
    N8N_MOCK_MODE: bool = Field(False, env="N8N_MOCK_MODE")

    EA_CALENDAR_BASE_URL: str = Field("", env="EA_CALENDAR_BASE_URL")
    EA_CALENDAR_TOKEN: str = Field("", env="EA_CALENDAR_TOKEN")
    EA_CALENDAR_PATH: str = Field("events", env="EA_CALENDAR_PATH")
    EA_TASKS_BASE_URL: str = Field("", env="EA_TASKS_BASE_URL")
    EA_TASKS_TOKEN: str = Field("", env="EA_TASKS_TOKEN")
    EA_TASKS_PATH: str = Field("tasks", env="EA_TASKS_PATH")

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
