# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_cohort_inventory_counts.py
import pytest

from app.services.ghl_service import GHLService


@pytest.mark.asyncio
async def test_cohort_inventory_counts_unscored_by_source(monkeypatch):
    service = GHLService()

    async def fake_get_all_contacts():
        return [
            {"id": "1", "source": "BAS", "customFields": []},
            {"id": "2", "source": "BAS", "customFields": [{"fieldKey": "contact.score_category", "value": "warm"}]},
            {"id": "3", "source": "Webinar", "customFields": []},
        ], {"status": "connected"}

    monkeypatch.setattr(service, "get_all_contacts", fake_get_all_contacts)

    inventory = await service.get_cohort_inventory()
    groups = {group["source"]: group for group in inventory["source_groups"]}

    assert groups["BAS"]["count"] == 2
    assert groups["BAS"]["unscored_count"] == 1
    assert groups["Webinar"]["unscored_count"] == 1
