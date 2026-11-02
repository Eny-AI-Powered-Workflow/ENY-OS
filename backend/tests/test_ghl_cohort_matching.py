# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_ghl_cohort_matching.py
import pytest

from app.services.ghl_service import GHLService


@pytest.mark.asyncio
async def test_unscored_cohort_matching_accepts_normalized_source_and_category_fields(monkeypatch):
    service = GHLService()

    async def fake_get_all_contacts():
        return [
            {
                "id": "contact-1",
                "name": "Alice Example",
                "source": "Bootcamp Waitlist",
                "tags": [],
                "customFields": [],
            },
            {
                "id": "contact-2",
                "name": "Already Classified",
                "source": "Bootcamp Waitlist",
                "tags": [],
                "customFields": [
                    {"fieldKey": "contact.score_category", "value": "warm"},
                ],
            },
        ], {"status": "connected"}

    monkeypatch.setattr(service, "get_all_contacts", fake_get_all_contacts)

    contacts = await service.get_unscored_source_contacts(
        "  BOOTCAMP   WAITLIST ",
        limit=25,
    )

    assert [contact["id"] for contact in contacts] == ["contact-1"]
