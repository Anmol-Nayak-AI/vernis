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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

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
        Index("ix_artworks_org_created", "organization_id", "created_at"),
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
        Index("ix_jobs_org_created", "organization_id", "created_at"),
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
        Index("ix_audit_org_time", "organization_id", "occurred_at"),
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
