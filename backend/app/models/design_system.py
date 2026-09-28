# /home/obed/Documents/Eny_consulting/Eny_consulting/backend/app/models/design_system.py

import uuid

from sqlalchemy import ARRAY, BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class DesignSystemDocument(Base):
    __tablename__ = "design_system_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    audience = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    provider = Column(String, nullable=False, default="manual_upload")
    source_status = Column(String, nullable=False, default="unverified")
    source_reference = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DesignSystemDocumentVersion(Base):
    __tablename__ = "design_system_document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("design_system_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False)
    change_note = Column(Text, nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignSystemDocumentEvent(Base):
    __tablename__ = "design_system_document_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("design_system_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignRequest(Base):
    __tablename__ = "design_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    brief = Column(Text, nullable=False)
    request_type = Column(String, nullable=False)
    audience = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="requested", index=True)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    campaign_name = Column(String, nullable=True)
    program_name = Column(String, nullable=True)
    source_content_id = Column(UUID(as_uuid=True), ForeignKey("marketing_content_items.id", ondelete="set null"), nullable=True)
    source_video_asset_id = Column(UUID(as_uuid=True), ForeignKey("marketing_video_assets.id", ondelete="set null"), nullable=True)
    reference_urls = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DesignRequestEvent(Base):
    __tablename__ = "design_request_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("design_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignTemplate(Base):
    __tablename__ = "design_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    audience = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, default="manual_canva")
    provider_template_id = Column(String, nullable=True)
    template_url = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="draft", index=True)
    base_brand_document_id = Column(UUID(as_uuid=True), ForeignKey("design_system_documents.id", ondelete="restrict"), nullable=False)
    base_brand_version = Column(Integer, nullable=False)
    locked_fields = Column(JSONB, nullable=False, default=list)
    locked_values = Column(JSONB, nullable=False, default=dict)
    editable_fields = Column(JSONB, nullable=False, default=list)
    canva_dataset = Column(JSONB, nullable=False, default=dict)
    usage_rights = Column(JSONB, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DesignTemplateVersion(Base):
    __tablename__ = "design_template_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("design_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False)
    change_note = Column(Text, nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignTemplateEvent(Base):
    __tablename__ = "design_template_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("design_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignAsset(Base):
    __tablename__ = "design_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    audience = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    provider = Column(String, nullable=False, default="manual_upload")
    request_id = Column(UUID(as_uuid=True), ForeignKey("design_requests.id", ondelete="set null"), nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("design_templates.id", ondelete="set null"), nullable=True)
    template_version = Column(Integer, nullable=True)
    locked_values_snapshot = Column(JSONB, nullable=False, default=dict)
    variant_values = Column(JSONB, nullable=False, default=dict)
    brand_document_id = Column(UUID(as_uuid=True), ForeignKey("design_system_documents.id", ondelete="restrict"), nullable=False)
    brand_version = Column(Integer, nullable=False)
    campaign_name = Column(String, nullable=True)
    program_name = Column(String, nullable=True)
    source_content_id = Column(UUID(as_uuid=True), ForeignKey("marketing_content_items.id", ondelete="set null"), nullable=True)
    source_video_asset_id = Column(UUID(as_uuid=True), ForeignKey("marketing_video_assets.id", ondelete="set null"), nullable=True)
    generation_prompt = Column(Text, nullable=True)
    generation_sources = Column(JSONB, nullable=False, default=list)
    generation_draft = Column(JSONB, nullable=False, default=dict)
    canva_job_id = Column(String, nullable=True)
    external_design_id = Column(String, nullable=True)
    external_design_url = Column(Text, nullable=True)
    external_edit_url = Column(Text, nullable=True)
    external_view_url = Column(Text, nullable=True)
    external_thumbnail_url = Column(Text, nullable=True)
    external_urls_expires_at = Column(DateTime(timezone=True), nullable=True)
    export_job_id = Column(String, nullable=True)
    usage_rights = Column(JSONB, nullable=False, default=dict)
    revision = Column(Integer, nullable=False, default=1)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DesignAssetFile(Base):
    __tablename__ = "design_asset_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("design_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    file_kind = Column(String, nullable=False)
    provider = Column(String, nullable=False, default="manual_upload")
    original_filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(Text, nullable=False, unique=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignAssetVersion(Base):
    __tablename__ = "design_asset_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("design_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    revision = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False)
    change_note = Column(Text, nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignAssetEvent(Base):
    __tablename__ = "design_asset_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("design_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CanvaOAuthState(Base):
    __tablename__ = "canva_oauth_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_hash = Column(String, nullable=False, unique=True)
    verifier_encrypted = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CanvaConnection(Base):
    __tablename__ = "canva_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, unique=True)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    scopes = Column(ARRAY(String), nullable=False, default=list)
    canva_user_id = Column(String, nullable=True)
    canva_team_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="connected")
    connected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DesignAiDraft(Base):
    __tablename__ = "design_ai_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("design_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    audience = Column(String, nullable=False)
    title = Column(String, nullable=False)
    visual_direction = Column(Text, nullable=False)
    copy_variants = Column(JSONB, nullable=False, default=list)
    template_suggestions = Column(JSONB, nullable=False, default=list)
    source_documents = Column(JSONB, nullable=False, default=list)
    prompt = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="draft")
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignFunnel(Base):
    __tablename__ = "design_funnels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    funnel_key = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    audience = Column(String, nullable=False, default="marketing")
    provider = Column(String, nullable=False, default="webflow")
    site_id = Column(String, nullable=True)
    collection_id = Column(String, nullable=True)
    page_id = Column(String, nullable=True)
    collection_item_id = Column(String, nullable=True)
    public_url = Column(Text, nullable=True)
    conversion_events = Column(JSONB, nullable=False, default=list)
    status = Column(String, nullable=False, default="draft", index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DesignFunnelVariant(Base):
    __tablename__ = "design_funnel_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    funnel_id = Column(UUID(as_uuid=True), ForeignKey("design_funnels.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    variant_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content_json = Column(JSONB, nullable=False)
    form_fields = Column(JSONB, nullable=False, default=list)
    conversion_event = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft", index=True)
    external_item_id = Column(String, nullable=True)
    previous_published_snapshot = Column(JSONB, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="set null"), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignFunnelEvent(Base):
    __tablename__ = "design_funnel_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    funnel_id = Column(UUID(as_uuid=True), ForeignKey("design_funnels.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("design_funnel_variants.id", ondelete="set null"), nullable=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    event_type = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DesignProviderEvent(Base):
    __tablename__ = "design_provider_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="restrict"), nullable=False)
    event_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
