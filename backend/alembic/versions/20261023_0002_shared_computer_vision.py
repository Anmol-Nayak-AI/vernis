"""Vernis Phase 2 shared computer-vision infrastructure.

Revision ID: 20261023_0002
Revises: 20261023_0001
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20261023_0002"
down_revision: str | None = "20261023_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "vernis"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("The production migration requires PostgreSQL; SQLite tests use SQLAlchemy metadata.")
    op.execute("create extension if not exists vector")
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_identifier", sa.String(120), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("task", sa.String(80), nullable=False),
        sa.Column("implementation", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("evaluation_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status in ('development','validated','retired')", name="ck_model_versions_status"),
        sa.PrimaryKeyConstraint("id", name="pk_model_versions"),
        sa.UniqueConstraint("model_identifier", "version", name="uq_model_versions_identifier_version"),
        schema=SCHEMA,
    )
    op.create_table(
        "asset_fingerprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("cryptographic_hash", sa.String(64), nullable=False),
        sa.Column("perceptual_hash", sa.String(16), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("color_mode", sa.String(16), nullable=False),
        sa.Column("metadata_summary", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_fingerprints_asset_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["model_version_id"], [f"{SCHEMA}.model_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_asset_fingerprints"),
        sa.UniqueConstraint("asset_id", "model_version_id", name="uq_fingerprints_asset_model"),
        schema=SCHEMA,
    )
    op.create_index("ix_fingerprints_org_phash", "asset_fingerprints", ["organization_id", "perceptual_hash"], schema=SCHEMA)
    op.create_table(
        "visual_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("embedding", Vector(96), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("norm", sa.String(24), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id", "asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_embeddings_asset_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["model_version_id"], [f"{SCHEMA}.model_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_visual_embeddings"),
        sa.UniqueConstraint("asset_id", "model_version_id", name="uq_embeddings_asset_model"),
        schema=SCHEMA,
    )
    op.create_index("ix_embeddings_org_model", "visual_embeddings", ["organization_id", "model_version_id"], schema=SCHEMA)
    op.execute(
        "create index ix_embeddings_hnsw_cosine on vernis.visual_embeddings "
        "using hnsw (embedding vector_cosine_ops)"
    )
    op.create_table(
        "image_comparisons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_asset_id", sa.Uuid(), nullable=False),
        sa.Column("target_asset_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("alignment", sa.JSON(), nullable=False),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("output_artifacts", sa.JSON(), nullable=False),
        sa.Column("evaluation_status", sa.String(40), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_comparisons_source_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "target_asset_id"],
            [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"],
            name="fk_comparisons_target_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["model_version_id"], [f"{SCHEMA}.model_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_image_comparisons"),
        schema=SCHEMA,
    )
    op.create_index("ix_comparisons_org_time", "image_comparisons", ["organization_id", sa.text("processed_at desc")], schema=SCHEMA)
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("fixture_name", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status in ('running','succeeded','failed')", name="ck_evaluation_runs_status"),
        sa.ForeignKeyConstraint(["model_version_id"], [f"{SCHEMA}.model_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_runs"),
        schema=SCHEMA,
    )
    _security()


def _security() -> None:
    op.execute(
        "revoke all on vernis.model_versions, vernis.asset_fingerprints, vernis.visual_embeddings, "
        "vernis.image_comparisons, vernis.evaluation_runs from anon, authenticated"
    )
    op.execute("grant select on vernis.model_versions, vernis.evaluation_runs to authenticated")
    op.execute(
        "grant select, insert, update on vernis.asset_fingerprints, vernis.visual_embeddings, "
        "vernis.image_comparisons to authenticated"
    )
    for table in ["asset_fingerprints", "visual_embeddings", "image_comparisons"]:
        op.execute(f"alter table vernis.{table} enable row level security")
        op.execute(f"alter table vernis.{table} force row level security")
        op.execute(
            f"create policy {table}_select_member on vernis.{table} for select to authenticated "
            "using (vernis_private.is_org_member(organization_id, null))"
        )
        op.execute(
            f"create policy {table}_insert_editor on vernis.{table} for insert to authenticated "
            "with check (vernis_private.is_org_member(organization_id, "
            "array['owner','administrator','investigator','conservator','analyst']))"
        )
        op.execute(
            f"create policy {table}_update_editor on vernis.{table} for update to authenticated "
            "using (vernis_private.is_org_member(organization_id, "
            "array['owner','administrator','investigator','conservator','analyst'])) "
            "with check (vernis_private.is_org_member(organization_id, "
            "array['owner','administrator','investigator','conservator','analyst']))"
        )


def downgrade() -> None:
    op.drop_table("evaluation_runs", schema=SCHEMA)
    op.drop_index("ix_comparisons_org_time", table_name="image_comparisons", schema=SCHEMA)
    op.drop_table("image_comparisons", schema=SCHEMA)
    op.execute("drop index if exists vernis.ix_embeddings_hnsw_cosine")
    op.drop_index("ix_embeddings_org_model", table_name="visual_embeddings", schema=SCHEMA)
    op.drop_table("visual_embeddings", schema=SCHEMA)
    op.drop_index("ix_fingerprints_org_phash", table_name="asset_fingerprints", schema=SCHEMA)
    op.drop_table("asset_fingerprints", schema=SCHEMA)
    op.drop_table("model_versions", schema=SCHEMA)
