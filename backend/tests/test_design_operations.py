from types import SimpleNamespace

from app.api.v1.endpoints.design_ai_funnels import _summarize_design_operations_metrics


def test_design_operations_summary_aggregates_turnaround_and_failures():
    result = _summarize_design_operations_metrics(
        requests=[
            SimpleNamespace(id="r1", created_at="2025-01-10T00:00:00Z", updated_at="2025-01-10T18:00:00Z", status="completed"),
            SimpleNamespace(id="r2", created_at="2025-01-11T00:00:00Z", updated_at="2025-01-12T12:00:00Z", status="completed"),
        ],
        assets=[
            SimpleNamespace(id="a1", created_at="2025-01-10T00:00:00Z", approved_at="2025-01-10T08:00:00Z"),
            SimpleNamespace(id="a2", created_at="2025-01-11T00:00:00Z", approved_at=None),
        ],
        templates=[
            SimpleNamespace(id="t1", template_key="welcome", usage_count=2),
            SimpleNamespace(id="t2", template_key="followup", usage_count=1),
        ],
        design_documents=[
            SimpleNamespace(audience="marketing", status="approved", source_status="verified"),
            SimpleNamespace(audience="marketing", status="changes_requested", source_status="unverified"),
            SimpleNamespace(audience="programs", status="draft", source_status="unverified"),
        ],
        funnel_experiments=[
            SimpleNamespace(status="completed", goal_event="lead_form_submit", winner_variant_id="v1", control_variant_id="v2", treatment_variant_id="v3"),
            SimpleNamespace(status="running", goal_event="lead_form_submit", winner_variant_id=None, control_variant_id="v2", treatment_variant_id="v3"),
        ],
        measurements=[
            SimpleNamespace(source="google", event_type="conversion", conversion_event="lead_form_submit", conversion_value=4),
            SimpleNamespace(source="linkedin", event_type="conversion", conversion_event="lead_form_submit", conversion_value=2),
            SimpleNamespace(source="google", event_type="visit", conversion_event=None, conversion_value=0),
        ],
        provider_events=[
            SimpleNamespace(provider="webflow", event_type="publish_failed", status="error", details={}),
            SimpleNamespace(provider="canva", event_type="export_failed", status="error", details={}),
            SimpleNamespace(provider="webflow", event_type="publish_succeeded", status="success", details={}),
        ],
        alerts=[
            SimpleNamespace(alert_type="webflow_publish_failed", status="open", source="webflow", severity="critical", message="Publish failed", details={}),
            SimpleNamespace(alert_type="tracking_outage", status="open", source="gtm", severity="warning", message="Tracking missing", details={}),
            SimpleNamespace(alert_type="design_form_broken", status="acknowledged", source="webflow", severity="warning", message="Form broken", details={}),
        ],
    )

    assert result["request_turnaround_hours"] == 18.0
    assert result["asset_approval_hours"] == 8.0
    assert result["template_reuse"][0]["template_key"] == "welcome"
    assert result["brand_review_outcomes"]["marketing"]["approved"] == 1
    assert result["funnel_publishing_failures"] == 1
    assert result["experiment_results"]["lead_form_submit"]["winner_rate"] == 0.5
    assert result["conversion_by_source"]["google"] == 4
    assert result["open_alerts"][0]["alert_type"] == "webflow_publish_failed"
