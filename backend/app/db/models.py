from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    desc,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.config import settings
from app.db.session import Base

SCHEMA = settings.database_schema


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["created_by"], [f"{SCHEMA}.users.id"], name="fk_organizations_created_by", ondelete="RESTRICT"
        ),
        CheckConstraint("plan in ('artist','professional','gallery','institution','enterprise')", name="plan"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String(32), default="artist", nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_memberships_organization", ondelete="CASCADE"
        ),
        ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.id"], name="fk_memberships_user", ondelete="CASCADE"),
        CheckConstraint(
            "role in ('owner','administrator','investigator','conservator','analyst','reviewer','viewer')",
            name="role",
        ),
        Index("ix_memberships_user_org", "user_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Artwork(Base, TimestampMixin):
    __tablename__ = "artworks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_artworks_organization", ondelete="CASCADE"
        ),
        ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.users.id"], name="fk_artworks_created_by", ondelete="RESTRICT"),
        CheckConstraint(
            "attribution_status in ('claimed','verified','disputed','unknown')", name="attribution_status"
        ),
        CheckConstraint("date_precision in ('exact','year','range','circa','unknown')", name="date_precision"),
        CheckConstraint("status in ('draft','active','archived')", name="status"),
        UniqueConstraint("organization_id", "id", name="uq_artworks_artwork_org_identity"),
        Index("ix_artworks_org_created", "organization_id", desc("created_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    artist_attribution: Mapped[str | None] = mapped_column(String(240))
    attribution_status: Mapped[str] = mapped_column(String(24), default="unknown", nullable=False)
    creation_year_from: Mapped[int | None] = mapped_column(Integer)
    creation_year_to: Mapped[int | None] = mapped_column(Integer)
    date_precision: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    medium: Mapped[str | None] = mapped_column(String(320))
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    current_custody: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)


class ArtworkAsset(Base, TimestampMixin):
    __tablename__ = "artwork_assets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_assets_organization", ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["organization_id", "artwork_id"],
            [f"{SCHEMA}.artworks.organization_id", f"{SCHEMA}.artworks.id"],
            name="fk_assets_artwork_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["uploaded_by"], [f"{SCHEMA}.users.id"], name="fk_assets_uploaded_by", ondelete="RESTRICT"),
        CheckConstraint("kind in ('primary_image','detail_image','document','condition_image')", name="kind"),
        CheckConstraint("status in ('pending','quarantined','ready','rejected')", name="status"),
        UniqueConstraint("organization_id", "id", name="uq_artwork_assets_asset_org_identity"),
        Index("ix_assets_org_artwork", "organization_id", "artwork_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    artwork_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="primary_image", nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    declared_mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    verified_mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    object_key: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(320))


class UploadIntent(Base):
    __tablename__ = "upload_intents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_upload_intents_organization", ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["organization_id", "asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_upload_intents_asset_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["created_by"], [f"{SCHEMA}.users.id"], name="fk_upload_intents_created_by", ondelete="RESTRICT"
        ),
        Index("ix_upload_intents_token_hash", "token_hash", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expected_mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_jobs_organization", ondelete="CASCADE"
        ),
        ForeignKeyConstraint(["requested_by"], [f"{SCHEMA}.users.id"], name="fk_jobs_requested_by", ondelete="RESTRICT"),
        CheckConstraint(
            "status in ('queued','running','awaiting_review','succeeded','partially_succeeded','failed','cancelling','cancelled')",
            name="status",
        ),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_jobs_job_idempotency"),
        Index("ix_jobs_org_created", "organization_id", desc("created_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(160))
    requested_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_audit_organization", ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(["actor_id"], [f"{SCHEMA}.users.id"], name="fk_audit_actor", ondelete="RESTRICT"),
        Index("ix_audit_org_time", "organization_id", desc("occurred_at")),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    request_id: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ModelVersion(Base, TimestampMixin):
    """Immutable registry entry for an inference implementation and its evaluation state."""

    __tablename__ = "model_versions"
    __table_args__ = (
        CheckConstraint("status in ('development','validated','retired')", name="status"),
        UniqueConstraint("model_identifier", "version", name="uq_model_versions_identifier_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    model_identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    task: Mapped[str] = mapped_column(String(80), nullable=False)
    implementation: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="development", nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evaluation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class AssetFingerprint(Base):
    __tablename__ = "asset_fingerprints"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_fingerprints_asset_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["model_version_id"], [f"{SCHEMA}.model_versions.id"], ondelete="RESTRICT"),
        UniqueConstraint("asset_id", "model_version_id", name="uq_fingerprints_asset_model"),
        Index("ix_fingerprints_org_phash", "organization_id", "perceptual_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    model_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    cryptographic_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    perceptual_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    color_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class VisualEmbedding(Base):
    __tablename__ = "visual_embeddings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_embeddings_asset_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["model_version_id"], [f"{SCHEMA}.model_versions.id"], ondelete="RESTRICT"),
        UniqueConstraint("asset_id", "model_version_id", name="uq_embeddings_asset_model"),
        Index("ix_embeddings_org_model", "organization_id", "model_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    model_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    # pgvector in PostgreSQL; ordinary JSON in the isolated SQLite test database.
    embedding: Mapped[list[float]] = mapped_column(Vector(96).with_variant(JSON, "sqlite"), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, default=96, nullable=False)
    norm: Mapped[str] = mapped_column(String(24), default="l2", nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ImageComparison(Base):
    __tablename__ = "image_comparisons"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "source_asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_comparisons_source_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "target_asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_comparisons_target_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["model_version_id"], [f"{SCHEMA}.model_versions.id"], ondelete="RESTRICT"),
        Index("ix_comparisons_org_time", "organization_id", desc("processed_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    model_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    alignment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    regions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    output_artifacts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evaluation_status: Mapped[str] = mapped_column(String(40), default="unreviewed", nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        ForeignKeyConstraint(["model_version_id"], [f"{SCHEMA}.model_versions.id"], ondelete="RESTRICT"),
        CheckConstraint("status in ('running','succeeded','failed')", name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    model_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    fixture_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class EngineCase(Base, TimestampMixin):
    __tablename__ = "engine_cases"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "artwork_id"],
            [f"{SCHEMA}.artworks.organization_id", f"{SCHEMA}.artworks.id"],
            name="fk_engine_cases_artwork_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT"),
        CheckConstraint(
            "engine in ('artsentinel','artshield','conservavision','musegraph','artvaluate','arttransit')",
            name="engine",
        ),
        CheckConstraint(
            "status in ('draft','queued','running','awaiting_review','approved','changes_requested','closed','failed')",
            name="status",
        ),
        UniqueConstraint("organization_id", "id", name="uq_engine_cases_case_org_identity"),
        Index("ix_engine_cases_org_engine_status", "organization_id", "engine", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    artwork_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    engine: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(24), default="not_assessed", nullable=False)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)


class EvidenceDocument(Base, TimestampMixin):
    __tablename__ = "evidence_documents"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "artwork_id"],
            [f"{SCHEMA}.artworks.organization_id", f"{SCHEMA}.artworks.id"],
            name="fk_evidence_artwork_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_evidence_asset_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT"),
        CheckConstraint(
            "kind in ('certificate','catalog','ownership','rights','condition_report','shipment','market_record','artist_statement','other')",
            name="kind",
        ),
        CheckConstraint("sensitivity in ('internal','restricted','public')", name="sensitivity"),
        CheckConstraint("verification_status in ('unverified','reviewed','verified','rejected')", name="verification_status"),
        UniqueConstraint("organization_id", "id", name="uq_evidence_documents_document_org_identity"),
        Index("ix_evidence_org_artwork", "organization_id", "artwork_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    artwork_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    title: Mapped[str] = mapped_column(String(320), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(2048))
    source_authority: Mapped[str | None] = mapped_column(String(320))
    content_sha256: Mapped[str | None] = mapped_column(String(64))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[str | None] = mapped_column(String(80))
    verification_status: Mapped[str] = mapped_column(String(24), default="unverified", nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(24), default="internal", nullable=False)
    external_ai_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "evidence_document_id"],
            [f"{SCHEMA}.evidence_documents.organization_id", f"{SCHEMA}.evidence_documents.id"],
            name="fk_evidence_chunks_document_tenant",
            ondelete="CASCADE",
        ),
        UniqueConstraint("evidence_document_id", "ordinal", name="uq_evidence_chunks_document_ordinal"),
        Index("ix_evidence_chunks_org_document", "organization_id", "evidence_document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    evidence_document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536).with_variant(JSON, "sqlite"))
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    citation_label: Mapped[str] = mapped_column(String(320), nullable=False)


class EvidenceClaim(Base, TimestampMixin):
    __tablename__ = "evidence_claims"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_evidence_claims_case_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "evidence_document_id"],
            [f"{SCHEMA}.evidence_documents.organization_id", f"{SCHEMA}.evidence_documents.id"],
            name="fk_evidence_claims_document_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("stance in ('supports','contradicts','context','unresolved')", name="stance"),
        CheckConstraint("review_status in ('unreviewed','accepted','rejected','needs_evidence')", name="review_status"),
        Index("ix_evidence_claims_org_case", "organization_id", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    stance: Mapped[str] = mapped_column(String(24), default="unresolved", nullable=False)
    confidence: Mapped[int | None] = mapped_column(Integer)
    review_status: Mapped[str] = mapped_column(String(24), default="unreviewed", nullable=False)
    source_locator: Mapped[str | None] = mapped_column(String(320))


class ProvenanceEvent(Base, TimestampMixin):
    __tablename__ = "provenance_events"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "artwork_id"],
            [f"{SCHEMA}.artworks.organization_id", f"{SCHEMA}.artworks.id"],
            name="fk_provenance_artwork_tenant",
            ondelete="CASCADE",
        ),
        CheckConstraint("verification_status in ('asserted','supported','verified','disputed')", name="verification_status"),
        Index("ix_provenance_org_artwork_date", "organization_id", "artwork_id", "date_from"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    artwork_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    date_from: Mapped[str | None] = mapped_column(String(32))
    date_to: Mapped[str | None] = mapped_column(String(32))
    actor_name: Mapped[str | None] = mapped_column(String(320))
    place_name: Mapped[str | None] = mapped_column(String(320))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(24), default="asserted", nullable=False)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class HumanReview(Base, TimestampMixin):
    __tablename__ = "human_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_human_reviews_case_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["reviewer_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT"),
        CheckConstraint("decision in ('approved','changes_requested','rejected')", name="decision"),
        Index("ix_human_reviews_org_case", "organization_id", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_agent_runs_case_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["job_id"], [f"{SCHEMA}.jobs.id"], ondelete="SET NULL"),
        CheckConstraint("status in ('queued','running','partially_succeeded','succeeded','failed')", name="status"),
        Index("ix_agent_runs_org_time", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    crew_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_identifier: Mapped[str | None] = mapped_column(String(120))
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    estimated_cost: Mapped[str | None] = mapped_column(String(40))
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ToolExecution(Base):
    __tablename__ = "tool_executions"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["agent_run_id"], [f"{SCHEMA}.agent_runs.id"], ondelete="CASCADE"),
        CheckConstraint("status in ('running','succeeded','failed')", name="status"),
        Index("ix_tool_executions_run_time", "agent_run_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportVersion(Base, TimestampMixin):
    __tablename__ = "report_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_report_versions_case_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT"),
        UniqueConstraint("case_id", "version", name="uq_report_versions_case_version"),
        Index("ix_report_versions_org_case", "organization_id", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    title: Mapped[str] = mapped_column(String(320), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)


class CopyrightMatch(Base, TimestampMixin):
    __tablename__ = "copyright_matches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_copyright_matches_case_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_copyright_matches_source_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "matched_asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_copyright_matches_target_tenant",
            ondelete="CASCADE",
        ),
        CheckConstraint("classification in ('style_similarity','near_duplicate','licensed','authorized','potential_reproduction','unreviewed')", name="classification"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    matched_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    similarity_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_record: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), default="unreviewed", nullable=False)
    review_notes: Mapped[str | None] = mapped_column(Text)


class ConditionInspection(Base, TimestampMixin):
    __tablename__ = "condition_inspections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_condition_inspections_case_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_condition_inspections_asset_tenant",
            ondelete="CASCADE",
        ),
        Index("ix_condition_inspections_org_case", "organization_id", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    environment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class DamageFinding(Base, TimestampMixin):
    __tablename__ = "damage_findings"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["inspection_id"], [f"{SCHEMA}.condition_inspections.id"], ondelete="CASCADE"),
        CheckConstraint("review_status in ('unreviewed','confirmed','dismissed')", name="review_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    inspection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    finding_type: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_region: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    measurements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[int | None] = mapped_column(Integer)
    review_status: Mapped[str] = mapped_column(String(24), default="unreviewed", nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class CollectionRecord(Base, TimestampMixin):
    __tablename__ = "collection_records"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "artwork_id"],
            [f"{SCHEMA}.artworks.organization_id", f"{SCHEMA}.artworks.id"],
            name="fk_collection_records_artwork_tenant",
            ondelete="CASCADE",
        ),
        UniqueConstraint("organization_id", "accession_number", name="uq_collection_records_org_accession"),
        Index("ix_collection_records_org_artwork", "organization_id", "artwork_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    artwork_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    accession_number: Mapped[str] = mapped_column(String(160), nullable=False)
    department: Mapped[str | None] = mapped_column(String(240))
    location: Mapped[str | None] = mapped_column(String(320))
    catalog_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_status: Mapped[str] = mapped_column(String(24), default="needs_review", nullable=False)


class CollectionRelationship(Base, TimestampMixin):
    __tablename__ = "collection_relationships"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["source_record_id"], [f"{SCHEMA}.collection_records.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["target_record_id"], [f"{SCHEMA}.collection_records.id"], ondelete="CASCADE"),
        CheckConstraint("verification_status in ('unverified','reviewed','verified','rejected')", name="verification_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_record_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_record_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(120), nullable=False)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(24), default="unverified", nullable=False)


class MarketComparable(Base, TimestampMixin):
    __tablename__ = "market_comparables"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_market_comparables_case_tenant",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(currency) = 3 and currency = upper(currency)", name="currency"),
        Index("ix_market_comparables_org_case", "organization_id", "case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_name: Mapped[str] = mapped_column(String(240), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(2048))
    source_record_id: Mapped[str] = mapped_column(String(240), nullable=False)
    artist_name: Mapped[str | None] = mapped_column(String(240))
    work_title: Mapped[str] = mapped_column(String(320), nullable=False)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    license_basis: Mapped[str] = mapped_column(String(320), nullable=False)


class ValuationReport(Base, TimestampMixin):
    __tablename__ = "valuation_reports"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_valuation_reports_case_tenant",
            ondelete="CASCADE",
        ),
        CheckConstraint("status in ('insufficient_market_evidence','research_estimate','reviewed')", name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(3))
    estimate_low_minor: Mapped[int | None] = mapped_column(BigInteger)
    estimate_mid_minor: Mapped[int | None] = mapped_column(BigInteger)
    estimate_high_minor: Mapped[int | None] = mapped_column(BigInteger)
    methodology: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "case_id"],
            [f"{SCHEMA}.engine_cases.organization_id", f"{SCHEMA}.engine_cases.id"],
            name="fk_shipments_case_tenant",
            ondelete="CASCADE",
        ),
        CheckConstraint("status in ('planned','packed','in_transit','arrived','review','closed')", name="status"),
        Index("ix_shipments_org_status", "organization_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    reference: Mapped[str] = mapped_column(String(160), nullable=False)
    origin: Mapped[str] = mapped_column(String(320), nullable=False)
    destination: Mapped[str] = mapped_column(String(320), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(24), default="planned", nullable=False)
    packaging: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    pre_asset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    arrival_asset_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class CustodyEvent(Base, TimestampMixin):
    __tablename__ = "custody_events"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["shipment_id"], [f"{SCHEMA}.shipments.id"], ondelete="CASCADE"),
        Index("ix_custody_events_shipment_time", "shipment_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    shipment_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    custodian: Mapped[str] = mapped_column(String(320), nullable=False)
    location: Mapped[str] = mapped_column(String(320), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    evidence_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class ArtworkPassport(Base, TimestampMixin):
    __tablename__ = "artwork_passports"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["organization_id", "artwork_id"],
            [f"{SCHEMA}.artworks.organization_id", f"{SCHEMA}.artworks.id"],
            name="fk_passports_artwork_tenant",
            ondelete="CASCADE",
        ),
        UniqueConstraint("artwork_id", "version", name="uq_passports_artwork_version"),
        Index("ix_passports_org_artwork", "organization_id", "artwork_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    artwork_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_completeness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    public_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        CheckConstraint("status in ('none','trialing','active','past_due','cancelled','incomplete')", name="status"),
        UniqueConstraint("organization_id", name="uq_subscriptions_organization"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    plan: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="none", nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="stripe", nullable=False)
    provider_customer_id: Mapped[str | None] = mapped_column(String(160), unique=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(160), unique=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Entitlement(Base, TimestampMixin):
    __tablename__ = "entitlements"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        UniqueConstraint("organization_id", "key", name="uq_entitlements_org_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    limit_value: Mapped[int | None] = mapped_column(Integer)
    metadata_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["actor_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_usage_events_org_idempotency"),
        Index("ix_usage_events_org_time", "organization_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    meter: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BillingWebhookEvent(Base):
    __tablename__ = "billing_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_billing_webhook_provider_event"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(80))
