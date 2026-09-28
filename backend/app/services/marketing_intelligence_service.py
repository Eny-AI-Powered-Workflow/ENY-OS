# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/marketing_intelligence_service.py

from typing import Any

from app.core.config import settings


class MarketingIntelligenceService:
    """Provider readiness and source metadata for Marketing intelligence."""

    def provider_status(self) -> dict[str, dict[str, Any]]:
        return {
            "google_search_console": {"configured": bool(settings.GSC_SERVICE_ACCOUNT_JSON), "source": "Google Search Console"},
            "ga4": {"configured": bool(settings.GA4_PROPERTY_ID and settings.GA4_SERVICE_ACCOUNT_JSON), "source": "Google Analytics 4"},
            "ahrefs": {"configured": bool(settings.AHREFS_API_KEY), "source": "Ahrefs"},
            "semrush": {"configured": bool(settings.SEMRUSH_API_KEY), "source": "Semrush"},
            "pagespeed": {"configured": bool(settings.PAGESPEED_API_KEY), "source": "PageSpeed Insights"},
            "dataforseo": {"configured": bool(settings.DATAFORSEO_LOGIN and settings.DATAFORSEO_PASSWORD), "source": "DataForSEO"},
            "serpapi": {"configured": bool(settings.SERPAPI_API_KEY), "source": "SerpApi"},
            "linkedin": {"configured": bool(settings.LINKEDIN_ACCESS_TOKEN), "source": "LinkedIn"},
            "meta": {"configured": bool(settings.META_ACCESS_TOKEN), "source": "Meta Graph API"},
            "x": {"configured": bool(settings.X_BEARER_TOKEN), "source": "X API"},
            "youtube": {"configured": bool(settings.YOUTUBE_API_KEY), "source": "YouTube"},
            "reddit": {"configured": bool(settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET), "source": "Reddit"},
            "slack": {"configured": bool(settings.SLACK_BOT_TOKEN), "source": "Slack"},
            "whisper": {"configured": bool(settings.OPENAI_API_KEY), "source": "OpenAI Whisper"},
            "private_video_storage": {"configured": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY), "source": "Private Supabase Storage"},
            "canva": {"configured": bool(settings.CANVA_ACCESS_TOKEN or (settings.CANVA_CLIENT_ID and settings.CANVA_CLIENT_SECRET)), "source": "Canva"},
        }

    def configured_sources(self, family: str) -> list[str]:
        providers = self.provider_status()
        seo = {"google_search_console", "ga4", "ahrefs", "semrush", "pagespeed", "dataforseo", "serpapi"}
        social = {"linkedin", "meta", "x", "youtube", "reddit", "slack"}
        allowed = seo if family == "seo" else social
        return [name for name in allowed if providers[name]["configured"]]


marketing_intelligence_service = MarketingIntelligenceService()
