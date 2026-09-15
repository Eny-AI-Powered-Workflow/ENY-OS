import pytest

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
