import pytest
from unittest.mock import AsyncMock

from app.services.ghl_service import GHLService


@pytest.mark.asyncio
async def test_get_enrollment_leads_filters_and_shapes_ghl_contacts(monkeypatch):
    service = GHLService()

    async def fake_get_all_contacts():
        return [
            {
                "id": "contact-1",
                "firstName": "Alice",
                "lastName": "Example",
                "email": "alice@example.com",
                "phone": "555-0001",
                "source": "Bootcamp",
                "tags": ["approved-batch"],
                "customFields": [
                    {"id": "caiccVdZ41m5BMyWMH57", "value": "92"},
                    {"id": "CiowYO5hnAmwWKCp7vAO", "value": "hot"},
                ],
            },
            {
                "id": "contact-2",
                "firstName": "Bob",
                "lastName": "Other",
                "email": "bob@example.com",
                "source": "Free Training",
                "customFields": [],
            },
        ], {"status": "connected"}

    monkeypatch.setattr(service, "get_all_contacts", fake_get_all_contacts)

    leads = await service.get_enrollment_leads(limit=20, search="alice")

    assert len(leads) == 1
    assert leads[0]["id"] == "contact-1"
    assert leads[0]["score"] == 92
    assert leads[0]["category"] == "hot"
    assert leads[0]["tags"] == ["approved-batch"]


@pytest.mark.asyncio
async def test_sync_enrollment_outcome_writes_tags_fields_and_note(monkeypatch):
    service = GHLService()
    service.get_contact = AsyncMock(return_value={"id": "contact-1", "tags": ["existing"]})
    service.update_contact = AsyncMock(return_value=True)
    service.add_contact_note = AsyncMock(return_value=True)

    result = await service.sync_enrollment_outcome(
        "contact-1",
        queue_status="contacted",
        score=92,
        category="hot",
        owner_id="owner-1",
        note="Follow-up completed",
    )

    assert result["success"] is True
    payload = service.update_contact.await_args.args[1]
    assert "eny-score-hot" in payload["tags"]
    assert "eny-status-contacted" in payload["tags"]
    assert "eny-owner-owner-1" in payload["tags"]
    assert {field["value"] for field in payload["customFields"]} >= {92, "hot", "contacted"}
    service.add_contact_note.assert_awaited_once_with("contact-1", "Follow-up completed")
