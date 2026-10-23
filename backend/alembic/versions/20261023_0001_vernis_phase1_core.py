"""Additive Vernis Phase 1 core schema.

Revision ID: 20261023_0001
Revises: None
Create Date: 2026-10-23

This migration does not rename or drop any legacy public tables.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "vernis"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("create extension if not exists pgcrypto")
        op.execute("create extension if not exists vector")
        op.execute(f"create schema if not exists {SCHEMA}")
    else:
        raise RuntimeError("The production migration requires PostgreSQL; use SQLAlchemy metadata for SQLite tests.")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        schema=SCHEMA,
    )
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("plan in ('artist','professional','gallery','institution','enterprise')", name="ck_organizations_plan"),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.users.id"], name="fk_organizations_created_by", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
        schema=SCHEMA,
    )
    op.create_table(
        "organization_memberships",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role in ('owner','administrator','investigator','conservator','analyst','reviewer','viewer')", name="ck_organization_memberships_role"),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_memberships_organization", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.id"], name="fk_memberships_user", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "user_id", name="pk_organization_memberships"),
        schema=SCHEMA,
    )
    op.create_index("ix_memberships_user_org", "organization_memberships", ["user_id", "organization_id"], schema=SCHEMA)
    op.create_table(
        "artworks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("artist_attribution", sa.String(240), nullable=True),
        sa.Column("attribution_status", sa.String(24), nullable=False),
        sa.Column("creation_year_from", sa.Integer(), nullable=True),
        sa.Column("creation_year_to", sa.Integer(), nullable=True),
        sa.Column("date_precision", sa.String(16), nullable=False),
        sa.Column("medium", sa.String(320), nullable=True),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_custody", sa.String(320), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("attribution_status in ('claimed','verified','disputed','unknown')", name="ck_artworks_attribution_status"),
        sa.CheckConstraint("date_precision in ('exact','year','range','circa','unknown')", name="ck_artworks_date_precision"),
        sa.CheckConstraint("status in ('draft','active','archived')", name="ck_artworks_status"),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_artworks_organization", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.users.id"], name="fk_artworks_created_by", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_artworks"),
        sa.UniqueConstraint("organization_id", "id", name="uq_artworks_artwork_org_identity"),
        schema=SCHEMA,
    )
    op.create_index("ix_artworks_org_created", "artworks", ["organization_id", sa.text("created_at desc")], schema=SCHEMA)
    op.create_table(
        "artwork_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("artwork_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("declared_mime_type", sa.String(128), nullable=False),
        sa.Column("verified_mime_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("object_key", sa.String(1024), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("rejection_reason", sa.String(320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind in ('primary_image','detail_image','document','condition_image')", name="ck_artwork_assets_kind"),
        sa.CheckConstraint("status in ('pending','quarantined','ready','rejected')", name="ck_artwork_assets_status"),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_assets_organization", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id", "artwork_id"], [f"{SCHEMA}.artworks.organization_id", f"{SCHEMA}.artworks.id"], name="fk_assets_artwork_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], [f"{SCHEMA}.users.id"], name="fk_assets_uploaded_by", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_artwork_assets"),
        sa.UniqueConstraint("organization_id", "id", name="uq_artwork_assets_asset_org_identity"),
        schema=SCHEMA,
    )
    op.create_index("ix_assets_org_artwork", "artwork_assets", ["organization_id", "artwork_id"], schema=SCHEMA)
    op.create_table(
        "upload_intents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expected_size", sa.BigInteger(), nullable=False),
        sa.Column("expected_mime_type", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_upload_intents_organization", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id", "asset_id"], [f"{SCHEMA}.artwork_assets.organization_id", f"{SCHEMA}.artwork_assets.id"], name="fk_upload_intents_asset_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.users.id"], name="fk_upload_intents_created_by", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_upload_intents"),
        schema=SCHEMA,
    )
    op.create_index("ix_upload_intents_token_hash", "upload_intents", ["token_hash"], unique=True, schema=SCHEMA)
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=True),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status in ('queued','running','awaiting_review','succeeded','partially_succeeded','failed','cancelling','cancelled')", name="ck_jobs_status"),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_jobs_organization", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], [f"{SCHEMA}.users.id"], name="fk_jobs_requested_by", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_jobs"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_jobs_job_idempotency"),
        schema=SCHEMA,
    )
    op.create_index("ix_jobs_org_created", "jobs", ["organization_id", sa.text("created_at desc")], schema=SCHEMA)
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], [f"{SCHEMA}.organizations.id"], name="fk_audit_organization", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_id"], [f"{SCHEMA}.users.id"], name="fk_audit_actor", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        schema=SCHEMA,
    )
    op.create_index("ix_audit_org_time", "audit_events", ["organization_id", sa.text("occurred_at desc")], schema=SCHEMA)

    _install_postgres_security()


def _install_postgres_security() -> None:
    op.execute("create schema if not exists vernis_private")
    op.execute("revoke all on schema vernis_private from public")
    op.execute(
        """
        create or replace function vernis_private.current_user_id()
        returns uuid language sql stable security invoker set search_path = '' as $$
          select coalesce(
            nullif(current_setting('request.jwt.claim.sub', true), ''),
            nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'
          )::uuid;
        $$
        """
    )
    op.execute(
        """
        create or replace function vernis_private.is_org_member(target_org uuid, allowed_roles text[] default null)
        returns boolean language sql stable security definer set search_path = '' as $$
          select exists (
            select 1 from vernis.organization_memberships m
            where m.organization_id = target_org
              and m.user_id = vernis_private.current_user_id()
              and (allowed_roles is null or m.role = any(allowed_roles))
          );
        $$
        """
    )
    op.execute(
        """
        create or replace function vernis_private.created_org(target_org uuid)
        returns boolean language sql stable security definer set search_path = '' as $$
          select exists (
            select 1 from vernis.organizations o
            where o.id = target_org
              and o.created_by = vernis_private.current_user_id()
          );
        $$
        """
    )
    op.execute("revoke all on function vernis_private.current_user_id() from public")
    op.execute("revoke all on function vernis_private.is_org_member(uuid, text[]) from public")
    op.execute("revoke all on function vernis_private.created_org(uuid) from public")
    op.execute("grant usage on schema vernis to authenticated")
    op.execute("grant usage on schema vernis_private to authenticated")
    op.execute("grant execute on function vernis_private.current_user_id() to authenticated")
    op.execute("grant execute on function vernis_private.is_org_member(uuid, text[]) to authenticated")
    op.execute("grant execute on function vernis_private.created_org(uuid) to authenticated")
    op.execute("revoke all on all tables in schema vernis from anon, authenticated")
    op.execute("grant select, insert, update on vernis.users, vernis.organizations, vernis.organization_memberships, vernis.artworks, vernis.artwork_assets to authenticated")
    op.execute("grant select on vernis.jobs, vernis.audit_events to authenticated")

    for table in ["users", "organizations", "organization_memberships", "artworks", "artwork_assets", "jobs", "audit_events"]:
        op.execute(f"alter table vernis.{table} enable row level security")
        op.execute(f"alter table vernis.{table} force row level security")

    policies = [
        "create policy users_select_self on vernis.users for select to authenticated using (id = vernis_private.current_user_id())",
        "create policy users_insert_self on vernis.users for insert to authenticated with check (id = vernis_private.current_user_id())",
        "create policy users_update_self on vernis.users for update to authenticated using (id = vernis_private.current_user_id()) with check (id = vernis_private.current_user_id())",
        "create policy organizations_select_member on vernis.organizations for select to authenticated using (vernis_private.is_org_member(id, null))",
        "create policy organizations_insert_owner on vernis.organizations for insert to authenticated with check (created_by = vernis_private.current_user_id())",
        "create policy organizations_update_manager on vernis.organizations for update to authenticated using (vernis_private.is_org_member(id, array['owner','administrator'])) with check (vernis_private.is_org_member(id, array['owner','administrator']))",
        "create policy memberships_select_member on vernis.organization_memberships for select to authenticated using (user_id = vernis_private.current_user_id() or vernis_private.is_org_member(organization_id, array['owner','administrator']))",
        "create policy memberships_insert_manager on vernis.organization_memberships for insert to authenticated with check (vernis_private.is_org_member(organization_id, array['owner','administrator']) or (user_id = vernis_private.current_user_id() and role = 'owner' and vernis_private.created_org(organization_id)))",
        "create policy memberships_update_manager on vernis.organization_memberships for update to authenticated using (vernis_private.is_org_member(organization_id, array['owner','administrator'])) with check (vernis_private.is_org_member(organization_id, array['owner','administrator']))",
        "create policy artworks_select_member on vernis.artworks for select to authenticated using (vernis_private.is_org_member(organization_id, null))",
        "create policy artworks_insert_editor on vernis.artworks for insert to authenticated with check (created_by = vernis_private.current_user_id() and vernis_private.is_org_member(organization_id, array['owner','administrator','investigator','conservator','analyst']))",
        "create policy artworks_update_editor on vernis.artworks for update to authenticated using (vernis_private.is_org_member(organization_id, array['owner','administrator','investigator','conservator','analyst'])) with check (vernis_private.is_org_member(organization_id, array['owner','administrator','investigator','conservator','analyst']))",
        "create policy assets_select_member on vernis.artwork_assets for select to authenticated using (vernis_private.is_org_member(organization_id, null))",
        "create policy assets_insert_editor on vernis.artwork_assets for insert to authenticated with check (uploaded_by = vernis_private.current_user_id() and vernis_private.is_org_member(organization_id, array['owner','administrator','investigator','conservator','analyst']))",
        "create policy assets_update_editor on vernis.artwork_assets for update to authenticated using (uploaded_by = vernis_private.current_user_id() or vernis_private.is_org_member(organization_id, array['owner','administrator'])) with check (vernis_private.is_org_member(organization_id, array['owner','administrator','investigator','conservator','analyst']))",
        "create policy jobs_select_member on vernis.jobs for select to authenticated using (vernis_private.is_org_member(organization_id, null))",
        "create policy audit_select_manager on vernis.audit_events for select to authenticated using (vernis_private.is_org_member(organization_id, array['owner','administrator']))",
    ]
    for policy in policies:
        op.execute(policy)


def downgrade() -> None:
    # A downgrade is intentionally scoped to the new schema only. It is never
    # run automatically against production data.
    op.execute("drop schema if exists vernis_private cascade")
    op.execute("drop schema if exists vernis cascade")
