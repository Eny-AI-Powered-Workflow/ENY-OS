# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/services/social_analytics_service.py

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.marketing_intelligence import SocialAccount, SocialMetricObservation, SocialPost
from app.services.ghl_service import ghl_service

SOCIAL_PLATFORMS = ("facebook", "linkedin", "instagram", "tiktok", "pinterest", "youtube", "x")
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
GHL_INSIGHTS_PLATFORMS = {"facebook", "instagram", "linkedin", "youtube"}
GHL_INSIGHT_METRICS = {"like": "likes", "share": "shares", "comment": "comments"}
PLATFORM_ALIASES = {"twitter": "x", "tiktok-business": "tiktok"}
CREDENTIAL_ENV_KEYS = {
    "linkedin": ("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_ORGANIZATION_ID"),
    "instagram": ("META_ACCESS_TOKEN", "META_INSTAGRAM_ACCOUNT_ID"),
    "facebook": ("META_ACCESS_TOKEN", "META_FACEBOOK_PAGE_ID"),
    "x": ("X_BEARER_TOKEN",),
    "tiktok": ("TIKTOK_ACCESS_TOKEN", "TIKTOK_ACCOUNT_ID"),
    "youtube": ("YOUTUBE_API_KEY", "YOUTUBE_CHANNEL_ID"),
    "pinterest": (),
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
            "pinterest": settings.BUFFER_PINTEREST_PROFILE_IDS,
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
                "api_collector_status": (
                    "configured"
                    if settings.GHL_PRIVATE_TOKEN and settings.GHL_LOCATION_ID
                    else "not_configured"
                ),
                "metrics_collection_status": (
                    "ghl_insights"
                    if platform in GHL_INSIGHTS_PLATFORMS
                    else "posts_only"
                ),
                "ghl_connection_status": (
                    "configured"
                    if settings.GHL_PRIVATE_TOKEN and settings.GHL_LOCATION_ID
                    else "not_configured"
                ),
                "insights_supported": platform in GHL_INSIGHTS_PLATFORMS,
                "connected_account_count": 0,
                "accounts": [],
                "recent_posts": [],
                "stats_status": "no_data",
                "posts_count": 0,
                "metrics": {},
                "latest_observed_at": None,
            }
        return platforms

    async def sync_from_ghl(self, db: Session, actor_id: Any, days: int = 30) -> dict[str, Any]:
        """Store GHL Social Planner accounts, published posts and supported insights."""
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=days)
        raw_accounts = await ghl_service.get_social_accounts()
        raw_posts, max_posts_reached = await ghl_service.get_social_posts(
            from_date=period_start.isoformat(),
            to_date=period_end.isoformat(),
        )
        observed_at = datetime.now(timezone.utc)
        location_id = settings.GHL_LOCATION_ID
        account_rows = (
            db.query(SocialAccount)
            .filter(SocialAccount.ghl_location_id == location_id)
            .all()
        )
        account_by_identity = {
            (account.platform, account.external_account_id): account
            for account in account_rows
        }
        for account in account_rows:
            account.active = False

        supported_accounts = 0
        for account_data in raw_accounts:
            platform = self._normalize_platform(account_data.get("platform"))
            account_id = account_data.get("id")
            if platform not in SOCIAL_PLATFORMS or not isinstance(account_id, str) or not account_id:
                continue
            identity = (platform, account_id)
            account = account_by_identity.get(identity)
            if account is None:
                account = SocialAccount(
                    ghl_location_id=location_id,
                    platform=platform,
                    external_account_id=account_id,
                    created_by=actor_id,
                )
                db.add(account)
                account_by_identity[identity] = account
            account.display_name = str(account_data.get("name") or platform.title())[:240]
            account.account_type = str(account_data["type"])[:80] if account_data.get("type") else None
            account.active = bool(account_data.get("active", True))
            account.is_expired = bool(account_data.get("isExpired", False))
            account.metadata_json = {
                "connection_source": account_data.get("connectionSource"),
            }
            account.synced_at = observed_at
            supported_accounts += 1

        posts_processed = 0
        metrics_recorded = 0
        skipped_posts = 0
        for post_data in raw_posts:
            platform = self._normalize_platform(post_data.get("platform"))
            published_at = self._parse_datetime(post_data.get("publishedAt") or post_data.get("displayDate"))
            external_post_id = post_data.get("postId") or post_data.get("_id")
            primary_account_id = post_data.get("accountId")
            account_ids = (
                [primary_account_id]
                if isinstance(primary_account_id, str) and primary_account_id
                else post_data.get("accountIds")
            )
            if not isinstance(account_ids, list):
                account_ids = []
            account_ids = list(dict.fromkeys(
                account_id for account_id in account_ids
                if isinstance(account_id, str) and account_id
            ))
            if (
                platform not in SOCIAL_PLATFORMS
                or published_at is None
                or not isinstance(external_post_id, (str, int))
                or not account_ids
            ):
                skipped_posts += 1
                continue

            insights = post_data.get("insights")
            insights = insights if isinstance(insights, dict) else {}
            for account_id in account_ids:
                post = (
                    db.query(SocialPost)
                    .filter(
                        SocialPost.platform == platform,
                        SocialPost.account_id == account_id,
                        SocialPost.external_post_id == str(external_post_id),
                    )
                    .first()
                )
                if post is None:
                    post = SocialPost(
                        platform=platform,
                        account_id=account_id,
                        external_post_id=str(external_post_id),
                        created_by=actor_id,
                    )
                    db.add(post)
                post.text = str(post_data.get("summary") or "")[:10000] or None
                post.permalink = self._safe_permalink(post_data.get("previewLink"))
                post.media_type = str(post_data.get("type") or "post")[:80]
                post.published_at = published_at
                post.metadata_json = {
                    "ghl_post_id": str(post_data.get("_id") or ""),
                    "status": post_data.get("status"),
                }
                db.flush()
                posts_processed += 1

                if platform not in GHL_INSIGHTS_PLATFORMS:
                    continue
                for ghl_metric, metric_key in GHL_INSIGHT_METRICS.items():
                    metric_value = insights.get(ghl_metric)
                    if (
                        isinstance(metric_value, bool)
                        or not isinstance(metric_value, (int, float))
                        or metric_value < 0
                    ):
                        continue
                    observation = (
                        db.query(SocialMetricObservation)
                        .filter(
                            SocialMetricObservation.post_id == post.id,
                            SocialMetricObservation.metric_key == metric_key,
                            SocialMetricObservation.observed_at == observed_at,
                        )
                        .first()
                    )
                    if observation is None:
                        observation = SocialMetricObservation(
                            post_id=post.id,
                            metric_key=metric_key,
                            created_by=actor_id,
                        )
                        db.add(observation)
                    observation.metric_value = metric_value
                    observation.unit = "count"
                    observation.provider = "ghl"
                    observation.source = "GHL Social Planner post insights"
                    observation.observed_at = observed_at
                    observation.metadata_json = {}
                    metrics_recorded += 1

        return {
            "status": "synced",
            "source": "ghl",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "synced_at": observed_at.isoformat(),
            "accounts_synced": supported_accounts,
            "posts_processed": posts_processed,
            "metrics_recorded": metrics_recorded,
            "skipped_posts": skipped_posts,
            "max_posts_reached": max_posts_reached,
        }

    @staticmethod
    def _normalize_platform(platform: Any) -> str:
        normalized = str(platform or "").strip().lower()
        return PLATFORM_ALIASES.get(normalized, normalized)

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _safe_permalink(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        return value[:2000]

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
        latest_metrics_by_post: dict[str, dict[str, float]] = {}
        for observation in observations:
            post = posts_by_id.get(observation.post_id)
            if post and post.platform in SOCIAL_PLATFORMS:
                latest.setdefault(
                    (post.platform, str(post.id), observation.metric_key), observation
                )
                latest_metrics_by_post.setdefault(str(post.id), {}).setdefault(
                    observation.metric_key,
                    float(observation.metric_value),
                )

        platforms = self.platform_status()
        accounts = (
            db.query(SocialAccount)
            .filter(SocialAccount.ghl_location_id == settings.GHL_LOCATION_ID)
            .all()
        )
        for account in accounts:
            platform = self._normalize_platform(account.platform)
            if platform not in platforms:
                continue
            platforms[platform]["accounts"].append({
                "id": account.external_account_id,
                "name": account.display_name,
                "type": account.account_type,
                "active": account.active,
                "expired": account.is_expired,
                "synced_at": account.synced_at.isoformat(),
            })
            if account.active and not account.is_expired:
                platforms[platform]["connected_account_count"] += 1
        totals: dict[str, dict[str, float]] = {platform: {} for platform in SOCIAL_PLATFORMS}
        metric_times: dict[str, dict[str, list[datetime]]] = {
            platform: {} for platform in SOCIAL_PLATFORMS
        }
        for post in posts:
            if post.platform in platforms:
                platforms[post.platform]["posts_count"] += 1
                if len(platforms[post.platform]["recent_posts"]) < 5:
                    platforms[post.platform]["recent_posts"].append({
                        "id": str(post.id),
                        "text": post.text,
                        "permalink": post.permalink,
                        "published_at": post.published_at.isoformat(),
                        "metrics": {},
                    })
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
            recent_posts_by_id = {
                post["id"]: post for post in status["recent_posts"]
            }
            for post_id, post_payload in recent_posts_by_id.items():
                post_payload["metrics"] = latest_metrics_by_post.get(post_id, {})
            status["stats_status"] = (
                "available"
                if metrics
                else "awaiting_metrics"
                if status["posts_count"] and status["insights_supported"]
                else "posts_only"
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
                "GHL Social Planner returns only likes, comments and shares for Facebook, Instagram, LinkedIn and YouTube; impressions, reach, saves, clicks, views and watch time are not included.",
                "GHL does not return post insights for TikTok or Pinterest.",
                "A configured GHL token is not an API health check. Use Sync from GHL to verify access and refresh stored data.",
                "Syncs are user-triggered; background refresh scheduling is not configured.",
            ],
        }


social_analytics_service = SocialAnalyticsService()
