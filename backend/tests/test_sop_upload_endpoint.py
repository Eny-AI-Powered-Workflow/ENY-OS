# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/tests/test_sop_upload_endpoint.py

import os
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/testdb")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.api.v1.endpoints import ai


@pytest.mark.asyncio
async def test_knowledge_departments_returns_all_database_roles():
    db = MagicMock()
    db.query.return_value.order_by.return_value.all.return_value = [
        ("ceo",),
        ("graphic_designer",),
        ("sales",),
    ]

    result = await ai.list_knowledge_departments(db)

    assert result == {"departments": ["ceo", "graphic_designer", "sales"]}


@pytest.mark.asyncio
async def test_document_upload_extracts_text_and_uses_shared_ingestion(monkeypatch):
    current_user = SimpleNamespace(id="publisher-1")
    db = MagicMock()
    ingest = AsyncMock(return_value={"status": "ingested", "chunks": 1})
    monkeypatch.setattr(ai.settings, "KNOWLEDGE_MAX_UPLOAD_MB", 1)
    monkeypatch.setattr(ai, "extract_sop_text", lambda _filename, _content: "Extracted procedure text.")
    monkeypatch.setattr(ai, "_ingest_knowledge_document", ingest)

    result = await ai.upload_knowledge_document(
        title="Enrollment procedure",
        department="enrollment",
        source="Uploaded handbook",
        file=UploadFile(filename="handbook.pdf", file=BytesIO(b"%PDF-1.7")),
        current_user=current_user,
        db=db,
    )

    request = ingest.await_args.args[0]
    assert request.content == "Extracted procedure text."
    assert request.title == "Enrollment procedure"
    assert request.department == "enrollment"
    assert result["chunks"] == 1
    ingest.assert_awaited_once_with(request, current_user, db)


@pytest.mark.asyncio
async def test_document_upload_rejects_files_above_configured_limit(monkeypatch):
    monkeypatch.setattr(ai.settings, "KNOWLEDGE_MAX_UPLOAD_MB", 1)
    upload = UploadFile(filename="large.pdf", file=BytesIO(b"x" * (1024 * 1024 + 1)))

    with pytest.raises(HTTPException) as error:
        await ai.upload_knowledge_document(
            title="Large SOP",
            department="enrollment",
            source="ENY internal SOP",
            file=upload,
            current_user=SimpleNamespace(id="publisher-1"),
            db=MagicMock(),
        )

    assert error.value.status_code == 413
