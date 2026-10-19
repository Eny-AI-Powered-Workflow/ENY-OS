# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/social_analytics_service.py

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.marketing_intelligence import SocialMetricObservation, SocialPost

SOCIAL_PLATFORMS = ("linkedin", "instagram", "facebook", "x", "tiktok", "youtube")
SOCIAL_METRICS = (
    "impressions",
    "reach",
    "likes",
    "comments",
    "shares",
    "saves",
    "clicks",
    "views",
    "watch_time_seconds",
)
CREDENTIAL_ENV_KEYS = {
    "linkedin": ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_ORGANIZATION_ID"),
    "instagram": ("META_ACCESS_TOKEN", "META_INSTAGRAM_ACCOUNT_ID"),
    "facebook": ("META_ACCESS_TOKEN", "META_FACEBOOK_PAGE_ID"),
    "x": ("X_BEARER_TOKEN",),
    "tiktok": ("TIKTOK_ACCESS_TOKEN", "TIKTOK_ACCOUNT_ID"),
    "youtube": ("YOUTUBE_API_KEY", "YOUTUBE_CHANNEL_ID"),
}


class SocialAnalyticsService:
    """Build platform-isolated and collective statistics from provider observations."""

    @staticmethod
    def _credentials_configured(platform: str) -> bool:
        return not SocialAnalyticsService._missing_credentials(platform)

    @staticmethod
    def _missing_credentials(platform: str) -> list[str]:
        return [
            key
            for key in CREDENTIAL_ENV_KEYS[platform]
            if not getattr(settings, key).strip()
        ]

    @staticmethod
    def buffer_profile_ids(platform: str) -> list[str]:
        platform_profiles = {
            "linkedin": settings.BUFFER_LINKEDIN_PROFILE_IDS,
            "instagram": settings.BUFFER_INSTAGRAM_PROFILE_IDS,
            "facebook": settings.BUFFER_FACEBOOK_PROFILE_IDS,
            "x": settings.BUFFER_X_PROFILE_IDS,
            "tiktok": settings.BUFFER_TIKTOK_PROFILE_IDS,
            "youtube": settings.BUFFER_YOUTUBE_PROFILE_IDS,
        }
        has_platform_specific_profiles = any(
            value.strip() for value in platform_profiles.values()
        )
        configured = (
            platform_profiles[platform]
            if has_platform_specific_profiles
            else settings.BUFFER_PROFILE_IDS
        )
        return [value.strip() for value in configured.split(",") if value.strip()]

    def platform_status(self) -> dict[str, dict[str, Any]]:
        platforms: dict[str, dict[str, Any]] = {}
        for platform in SOCIAL_PLATFORMS:
            profiles = self.buffer_profile_ids(platform)
            missing_publishing = []
            if not settings.BUFFER_ACCESS_TOKEN:
                missing_publishing.append("BUFFER_ACCESS_TOKEN")
            if not profiles:
                missing_publishing.append(
                    f"BUFFER_{platform.upper()}_PROFILE_IDS"
                    if any(
                        getattr(settings, f"BUFFER_{name.upper()}_PROFILE_IDS").strip()
                        for name in SOCIAL_PLATFORMS
                    )
                    else "BUFFER_PROFILE_IDS"
                )
            platforms[platform] = {
                "platform": platform,
                "credentials_status": "configured" if self._credentials_configured(platform) else "missing",
                "required_credentials": list(CREDENTIAL_ENV_KEYS[platform]),
                "missing_credentials": self._missing_credentials(platform),
                "publishing_status": (
                    "configured"
                    if settings.BUFFER_ACCESS_TOKEN and profiles
                    else "not_configured"
                ),
                "missing_publishing_configuration": missing_publishing,
                "api_collector_status": "not_implemented",
                "metrics_collection_status": "manual_ingestion_only",
                "stats_status": "no_data",
                "posts_count": 0,
                "metrics": {},
                "latest_observed_at": None,
            }
        return platforms

    def analytics(self, db: Session, days: int = 30) -> dict[str, Any]:
        period_end = datetime.now(timezone.utc)
        since = period_end - timedelta(days=days)
        posts = (
            db.query(SocialPost)
            .filter(SocialPost.published_at >= since, SocialPost.published_at <= period_end)
            .order_by(SocialPost.published_at.desc())
            .limit(5000)
            .all()
        )
        posts_by_id = {post.id: post for post in posts}
        observations = []
        if posts_by_id:
            observations = (
                db.query(SocialMetricObservation)
                .filter(
                    SocialMetricObservation.post_id.in_(posts_by_id),
                    SocialMetricObservation.observed_at >= since,
                    SocialMetricObservation.observed_at <= period_end,
                )
                .order_by(SocialMetricObservation.observed_at.desc())
                .limit(20000)
                .all()
            )

        latest: dict[tuple[str, str, str], SocialMetricObservation] = {}
        for observation in observations:
            post = posts_by_id.get(observation.post_id)
            if post and post.platform in SOCIAL_PLATFORMS:
                latest.setdefault(
                    (post.platform, str(post.id), observation.metric_key), observation
                )

        platforms = self.platform_status()
        totals: dict[str, dict[str, float]] = {platform: {} for platform in SOCIAL_PLATFORMS}
        metric_times: dict[str, dict[str, list[datetime]]] = {
            platform: {} for platform in SOCIAL_PLATFORMS
        }
        for post in posts:
            if post.platform in platforms:
                platforms[post.platform]["posts_count"] += 1
        for (platform, _, metric_key), observation in latest.items():
            value = float(observation.metric_value)
            totals[platform][metric_key] = totals[platform].get(metric_key, 0.0) + value
            metric_times[platform].setdefault(metric_key, []).append(observation.observed_at)

        for platform, platform_totals in totals.items():
            metrics = {}
            for metric_key, value in platform_totals.items():
                timestamps = metric_times[platform][metric_key]
                metrics[metric_key] = {
                    "value": value,
                    "unit": "seconds" if metric_key == "watch_time_seconds" else "count",
                    "latest_observed_at": max(timestamps).isoformat(),
                }
            status = platforms[platform]
            status["metrics"] = metrics
            status["stats_status"] = (
                "available"
                if metrics
                else "awaiting_metrics"
                if status["posts_count"]
                else "no_data"
            )
            all_times = [item for values in metric_times[platform].values() for item in values]
            status["latest_observed_at"] = max(all_times).isoformat() if all_times else None

        collective_metrics: dict[str, dict[str, Any]] = {}
        for metric_key in SOCIAL_METRICS:
            contributors = [
                platform
                for platform in SOCIAL_PLATFORMS
                if metric_key in platforms[platform]["metrics"]
            ]
            if not contributors:
                continue
            collective_metrics[metric_key] = {
                "value": sum(
                    platforms[platform]["metrics"][metric_key]["value"]
                    for platform in contributors
                ),
                "unit": "seconds" if metric_key == "watch_time_seconds" else "count",
                "reporting_platforms": contributors,
                "missing_platforms": [
                    platform for platform in SOCIAL_PLATFORMS if platform not in contributors
                ],
            }

        return {
            "period_days": days,
            "period_start": since.isoformat(),
            "period_end": period_end.isoformat(),
            "platforms": platforms,
            "collective": {
                "platform_count": len(SOCIAL_PLATFORMS),
                "reporting_platforms": [
                    platform
                    for platform in SOCIAL_PLATFORMS
                    if platforms[platform]["stats_status"] == "available"
                ],
                "missing_platforms": [
                    platform
                    for platform in SOCIAL_PLATFORMS
                    if platforms[platform]["stats_status"] != "available"
                ],
                "posts_count": sum(
                    status["posts_count"] for status in platforms.values()
                ),
                "metrics": collective_metrics,
            },
            "notes": [
                "Values are the latest available snapshot per post and metric for posts published in the selected period.",
                "Collective totals include only platforms reporting each metric; metric definitions can vary by platform.",
                "Platform API metric collectors are not implemented. Metrics can be recorded through the authenticated ingestion endpoint.",
                "Credential presence is not an API health check and does not indicate that automatic collection is running.",
            ],
        }


social_analytics_service = SocialAnalyticsService()
