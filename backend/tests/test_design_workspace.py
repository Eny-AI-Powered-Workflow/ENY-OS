# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_design_workspace.py

from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.design_workspace import _validate_asset_usage_rights, _validate_template_snapshot
from app.models.design_system import DesignAsset, DesignTemplate
from app.services.design_asset_service import DesignAssetService


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeDb:
    def __init__(self, template):
        self.template = template

    def query(self, model):
        assert model is DesignTemplate
        return FakeQuery(self.template)


def test_template_snapshot_rejects_variant_overriding_locked_field():
    template = SimpleNamespace(
        status="approved",
        version=4,
        base_brand_document_id="brand-doc-1",
        base_brand_version=3,
        locked_values={"logo": "approved-logo-v2"},
        locked_fields=["logo"],
        editable_fields=["headline"],
    )
    asset = SimpleNamespace(
        template_id=uuid4(),
        template_version=4,
        brand_document_id="brand-doc-1",
        brand_version=3,
        locked_values_snapshot={"logo": "approved-logo-v2"},
        variant_values={"logo": "replacement-logo"},
    )

    with pytest.raises(HTTPException) as error:
        _validate_template_snapshot(FakeDb(template), asset)

    assert error.value.status_code == 409


def test_template_snapshot_rejects_changed_locked_values():
    template = SimpleNamespace(status="approved", version=2, base_brand_document_id="brand-doc-2", base_brand_version=1, locked_values={"logo": "new"}, locked_fields=["logo"], editable_fields=[])
    asset = SimpleNamespace(template_id=uuid4(), template_version=2, brand_document_id="brand-doc-2", brand_version=1, locked_values_snapshot={"logo": "old"}, variant_values={})

    with pytest.raises(HTTPException) as error:
        _validate_template_snapshot(FakeDb(template), asset)

    assert error.value.status_code == 409


def test_asset_usage_rights_reject_expired_license():
    asset = SimpleNamespace(usage_rights={"rights_basis": "licensed", "permitted_uses": ["web"], "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()})

    with pytest.raises(HTTPException) as error:
        _validate_asset_usage_rights(asset)

    assert error.value.status_code == 409


def test_private_upload_rejects_unsupported_mime_before_storage():
    class Upload:
        content_type = "image/svg+xml"
        filename = "unsafe.svg"
        file = None

    with pytest.raises(HTTPException) as error:
        __import__("asyncio").run(DesignAssetService().upload(Upload(), 100, "marketing"))

    assert error.value.status_code == 415


def test_private_upload_rejects_spoofed_image_mime_before_storage():
    from starlette.datastructures import UploadFile

    upload = UploadFile(filename="spoofed.png", file=BytesIO(b"<html>not an image"), headers={"content-type": "image/png"})

    with pytest.raises(HTTPException) as error:
        __import__("asyncio").run(DesignAssetService().upload(upload, 20, "marketing"))

    assert error.value.status_code == 415
