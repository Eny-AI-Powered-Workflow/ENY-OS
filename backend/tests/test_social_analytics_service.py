# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_social_analytics_service.py

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.marketing import SocialPostObservationRequest
from app.core.config import settings
from app.models.marketing_intelligence import SocialMetricObservation, SocialPost
from app.services.social_analytics_service import SOCIAL_PLATFORMS, SocialAnalyticsService


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def all(self):
        return self.rows


class FakeDatabase:
    def __init__(self, posts, observations):
        self.posts = posts
        self.observations = observations

    def query(self, model):
        if model is SocialPost:
            return FakeQuery(self.posts)
        if model is SocialMetricObservation:
            return FakeQuery(self.observations)
        raise AssertionError(f"Unexpected model queried: {model}")


def test_analytics_keeps_platform_stats_independent_and_collects_available_totals():
    now = datetime.now(timezone.utc)
    linkedin_post = SimpleNamespace(id=uuid4(), platform="linkedin", published_at=now)
    youtube_post = SimpleNamespace(id=uuid4(), platform="youtube", published_at=now)
    observations = [
        SimpleNamespace(
            id=uuid4(), post_id=linkedin_post.id, metric_key="reach",
            metric_value=120, observed_at=now,
        ),
        SimpleNamespace(
            id=uuid4(), post_id=linkedin_post.id, metric_key="likes",
            metric_value=12, observed_at=now,
        ),
        SimpleNamespace(
            id=uuid4(), post_id=youtube_post.id, metric_key="views",
            metric_value=450, observed_at=now,
        ),
    ]
    report = SocialAnalyticsService().analytics(
        FakeDatabase([linkedin_post, youtube_post], observations), days=30
    )

    assert tuple(report["platforms"]) == SOCIAL_PLATFORMS
    assert report["platforms"]["linkedin"]["metrics"]["reach"]["value"] == 120
    assert report["platforms"]["youtube"]["metrics"]["views"]["value"] == 450
    assert report["platforms"]["instagram"]["stats_status"] == "no_data"
    assert report["collective"]["posts_count"] == 2
    assert report["collective"]["metrics"]["reach"]["reporting_platforms"] == ["linkedin"]
    assert report["collective"]["metrics"]["reach"]["missing_platforms"] == [
        "instagram", "facebook", "x", "tiktok", "youtube",
    ]
    assert report["collective"]["metrics"]["views"]["value"] == 450


def test_social_post_request_requires_timezone_and_unique_metric_snapshots():
    published_at = datetime.now(timezone.utc)
    base = {
        "platform": "x",
        "account_id": "eny-account",
        "external_post_id": "post-1",
        "published_at": published_at,
    }
    SocialPostObservationRequest.model_validate(base)

    with pytest.raises(ValidationError, match="must include a timezone"):
        SocialPostObservationRequest.model_validate({
            **base,
            "published_at": published_at.replace(tzinfo=None),
        })

    metric = {"metric_key": "likes", "value": 3, "observed_at": published_at}
    with pytest.raises(ValidationError, match="only be submitted once"):
        SocialPostObservationRequest.model_validate({**base, "metrics": [metric, metric]})


def test_platform_specific_buffer_profiles_do_not_fall_back_to_other_profiles(monkeypatch):
    service = SocialAnalyticsService()
    monkeypatch.setattr(settings, "BUFFER_PROFILE_IDS", "legacy-profile")
    monkeypatch.setattr(settings, "BUFFER_INSTAGRAM_PROFILE_IDS", "instagram-profile")
    monkeypatch.setattr(settings, "BUFFER_LINKEDIN_PROFILE_IDS", "")
    monkeypatch.setattr(settings, "BUFFER_FACEBOOK_PROFILE_IDS", "")
    monkeypatch.setattr(settings, "BUFFER_X_PROFILE_IDS", "")
    monkeypatch.setattr(settings, "BUFFER_TIKTOK_PROFILE_IDS", "")
    monkeypatch.setattr(settings, "BUFFER_YOUTUBE_PROFILE_IDS", "")

    assert service.buffer_profile_ids("instagram") == ["instagram-profile"]
    assert service.buffer_profile_ids("linkedin") == []
