# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_social_analytics_service.py

from datetime import datetime, timezone
import operator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.marketing import SocialPostObservationRequest
from app.core.config import settings
from app.models.marketing_intelligence import (
    SocialAccount,
    SocialAnalyticsSyncState,
    SocialMetricObservation,
    SocialPost,
)
from app.services.ghl_service import GHLService
from app.services.social_analytics_service import SOCIAL_PLATFORMS, SocialAnalyticsService


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *criteria):
        for criterion in criteria:
            if getattr(criterion, "operator", None) is not operator.eq:
                continue
            column_name = getattr(criterion.left, "key", None)
            expected = getattr(criterion.right, "value", None)
            if column_name:
                self.rows = [
                    row for row in self.rows
                    if getattr(row, column_name, None) == expected
                ]
        return self

    def order_by(self, *_args):
        return self

    def limit(self, *_args):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeDatabase:
    def __init__(self, posts, observations, accounts=None, sync_states=None):
        self.posts = posts
        self.observations = observations
        self.accounts = accounts or []
        self.sync_states = sync_states or []

    def query(self, model):
        if model is SocialPost:
            return FakeQuery(self.posts)
        if model is SocialMetricObservation:
            return FakeQuery(self.observations)
        if model is SocialAccount:
            return FakeQuery(self.accounts)
        if model is SocialAnalyticsSyncState:
            return FakeQuery(self.sync_states)
        raise AssertionError(f"Unexpected model queried: {model}")

    def add(self, row):
        if isinstance(row, SocialPost):
            self.posts.append(row)
        elif isinstance(row, SocialMetricObservation):
            self.observations.append(row)
        elif isinstance(row, SocialAccount):
            self.accounts.append(row)
        elif isinstance(row, SocialAnalyticsSyncState):
            self.sync_states.append(row)
        else:
            raise AssertionError(f"Unexpected row added: {type(row)}")

    def flush(self):
        for row in [*self.posts, *self.observations, *self.accounts]:
            if row.id is None:
                row.id = uuid4()


def test_analytics_keeps_platform_stats_independent_and_collects_available_totals():
    now = datetime.now(timezone.utc)
    linkedin_post = SimpleNamespace(
        id=uuid4(), platform="linkedin", published_at=now, text=None, permalink=None
    )
    youtube_post = SimpleNamespace(
        id=uuid4(), platform="youtube", published_at=now, text=None, permalink=None
    )
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
    assert report["platforms"]["pinterest"]["insights_supported"] is False
    assert report["collective"]["posts_count"] == 2
    assert report["collective"]["metrics"]["reach"]["reporting_platforms"] == ["linkedin"]
    assert report["collective"]["metrics"]["reach"]["missing_platforms"] == [
        "facebook", "instagram", "tiktok", "pinterest", "youtube", "x",
    ]
    assert report["collective"]["metrics"]["views"]["value"] == 450


def test_sync_failure_is_persisted_and_returned_in_report(monkeypatch):
    monkeypatch.setattr(settings, "GHL_LOCATION_ID", "location-1")
    db = FakeDatabase(posts=[], observations=[])

    SocialAnalyticsService.record_sync_failure(
        db, uuid4(), 30, "GHL Social Planner returned HTTP 403."
    )
    report = SocialAnalyticsService().analytics(db, days=30)

    assert report["sync"]["status"] == "error"
    assert report["sync"]["last_error"] == "GHL Social Planner returned HTTP 403."
    assert report["sync"]["last_success_at"] is None


@pytest.mark.asyncio
async def test_sync_from_ghl_records_posts_accounts_and_supported_insights(monkeypatch):
    now = datetime.now(timezone.utc)
    account_data = [
        {"id": "facebook-account", "name": "ENY Facebook", "platform": "facebook", "active": True},
        {"id": "pinterest-account", "name": "ENY Pinterest", "platform": "pinterest", "active": True},
    ]
    post_data = [{
        "_id": "ghl-post-1",
        "postId": "facebook-post-1",
        "platform": "facebook",
        "accountId": "facebook-account",
        "summary": "A published update",
        "previewLink": "https://example.com/post",
        "publishedAt": now.isoformat(),
        "insights": {"like": 14, "share": 2, "comment": 3},
    }, {
        "_id": "ghl-post-2",
        "postId": "pinterest-post-1",
        "platform": "pinterest",
        "accountId": "pinterest-account",
        "summary": "A Pinterest post",
        "previewLink": "javascript:alert(1)",
        "publishedAt": now.isoformat(),
    }]

    class FakeGhl:
        async def get_social_accounts(self):
            return account_data

        async def get_social_posts(self, **_kwargs):
            return post_data, False

    monkeypatch.setattr("app.services.social_analytics_service.ghl_service", FakeGhl())
    monkeypatch.setattr(settings, "GHL_LOCATION_ID", "location-1")
    db = FakeDatabase(posts=[], observations=[])

    result = await SocialAnalyticsService().sync_from_ghl(db, uuid4(), days=30)

    assert result["status"] == "synced"
    assert result["accounts_synced"] == 2
    assert result["posts_processed"] == 2
    assert result["metrics_recorded"] == 3
    assert result["skipped_posts"] == 0
    assert len(db.sync_states) == 1
    assert db.sync_states[0].last_success_at is not None
    assert db.sync_states[0].last_error is None
    facebook_post = next(post for post in db.posts if post.platform == "facebook")
    assert facebook_post.external_post_id == "facebook-post-1"
    pinterest_post = next(post for post in db.posts if post.platform == "pinterest")
    assert pinterest_post.permalink is None
    assert {observation.metric_key for observation in db.observations} == {
        "likes", "shares", "comments",
    }
    report = SocialAnalyticsService().analytics(db, days=30)
    assert report["platforms"]["facebook"]["recent_posts"][0]["text"] == "A published update"
    assert report["platforms"]["facebook"]["recent_posts"][0]["metrics"]["likes"] == 14
    assert report["platforms"]["facebook"]["connected_account_count"] == 1
    assert report["platforms"]["pinterest"]["stats_status"] == "posts_only"
    assert report["sync"]["status"] == "connected"
    assert report["sync"]["posts_processed"] == 2


@pytest.mark.asyncio
async def test_ghl_social_api_uses_v3_and_string_pagination(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, **kwargs):
            calls.append(("get", url, kwargs))
            return FakeResponse({"success": True, "results": {"accounts": []}})

        async def post(self, url, **kwargs):
            calls.append(("post", url, kwargs))
            page_number = int(kwargs["json"]["skip"])
            return FakeResponse({
                "success": True,
                "results": {
                    "posts": [{"_id": f"post-{page_number}"}],
                    "count": 3,
                },
            })

    monkeypatch.setattr("app.services.ghl_service.httpx.AsyncClient", FakeClient)
    service = GHLService()
    service.private_token = "test-token"
    service.location_id = "location/with-slash"

    accounts = await service.get_social_accounts()
    posts, capped = await service.get_social_posts(
        "2026-01-01T00:00:00+00:00",
        "2026-01-31T00:00:00+00:00",
        max_posts=2,
        page_size=1,
    )

    assert accounts == []
    assert len(posts) == 2
    assert capped is True
    assert calls[0][1].endswith("/social-media-posting/location%2Fwith-slash/accounts")
    assert calls[0][2]["headers"]["Version"] == "v3"
    assert [call[2]["json"]["skip"] for call in calls[1:]] == ["0", "1"]
    assert all(call[2]["json"]["limit"] == "1" for call in calls[1:])
    assert all(call[2]["headers"]["Version"] == "v3" for call in calls[1:])


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
