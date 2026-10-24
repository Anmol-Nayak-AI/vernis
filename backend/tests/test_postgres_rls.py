from __future__ import annotations

import os
import uuid

import psycopg
import pytest


@pytest.mark.postgres
def test_postgres_rls_hides_other_tenants_and_enforces_editor_roles() -> None:
    database_url = os.getenv("VERNIS_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("VERNIS_TEST_DATABASE_URL is not configured")

    owner_a, owner_b, viewer_a = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    org_a, org_b = uuid.uuid4(), uuid.uuid4()
    connection = psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://"))
    try:
        with connection.cursor() as cursor:
            artwork_a, artwork_b = uuid.uuid4(), uuid.uuid4()
            cursor.executemany(
                "insert into vernis.users (id, email, display_name) values (%s, %s, %s)",
                [
                    (owner_a, "owner-a@example.test", "Owner A"),
                    (owner_b, "owner-b@example.test", "Owner B"),
                    (viewer_a, "viewer-a@example.test", "Viewer A"),
                ],
            )
            cursor.executemany(
                "insert into vernis.organizations (id, name, slug, plan, created_by) values (%s, %s, %s, 'gallery', %s)",
                [
                    (org_a, "Tenant A", f"tenant-a-{org_a.hex}", owner_a),
                    (org_b, "Tenant B", f"tenant-b-{org_b.hex}", owner_b),
                ],
            )
            cursor.executemany(
                "insert into vernis.organization_memberships (organization_id, user_id, role) values (%s, %s, %s)",
                [(org_a, owner_a, "owner"), (org_a, viewer_a, "viewer"), (org_b, owner_b, "owner")],
            )
            cursor.executemany(
                """insert into vernis.artworks
                   (id, organization_id, title, attribution_status, date_precision, dimensions, status, created_by)
                   values (%s, %s, %s, 'unknown', 'unknown', '{}'::jsonb, 'draft', %s)""",
                [
                    (artwork_a, org_a, "Tenant A work", owner_a),
                    (artwork_b, org_b, "Tenant B work", owner_b),
                ],
            )
            cursor.executemany(
                """insert into vernis.engine_cases
                   (id, organization_id, artwork_id, engine, title, status, risk_level, input_data, limitations, created_by)
                   values (%s, %s, %s, 'artsentinel', %s, 'draft', 'not_assessed', '{}'::jsonb, '[]'::jsonb, %s)""",
                [
                    (uuid.uuid4(), org_a, artwork_a, "Tenant A case", owner_a),
                    (uuid.uuid4(), org_b, artwork_b, "Tenant B case", owner_b),
                ],
            )
            cursor.executemany(
                """insert into vernis.evidence_documents
                   (id, organization_id, artwork_id, title, kind, verification_status, sensitivity,
                    external_ai_consent, metadata_fields, created_by)
                   values (%s, %s, %s, %s, 'other', 'unverified', %s, false, '{}'::jsonb, %s)""",
                [
                    (uuid.uuid4(), org_a, artwork_a, "Tenant A internal", "internal", owner_a),
                    (uuid.uuid4(), org_a, artwork_a, "Tenant A restricted", "restricted", owner_a),
                    (uuid.uuid4(), org_b, artwork_b, "Tenant B internal", "internal", owner_b),
                ],
            )

            cursor.execute("set local role authenticated")
            cursor.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(owner_a),))
            cursor.execute("select organization_id, title from vernis.artworks where organization_id in (%s, %s)", (org_a, org_b))
            assert cursor.fetchall() == [(org_a, "Tenant A work")]
            cursor.execute("select title from vernis.engine_cases order by title")
            assert cursor.fetchall() == [("Tenant A case",)]
            cursor.execute("select title from vernis.evidence_documents order by title")
            assert cursor.fetchall() == [("Tenant A internal",), ("Tenant A restricted",)]

            cursor.execute("savepoint cross_tenant_write")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute(
                    """insert into vernis.artworks
                       (organization_id, title, attribution_status, date_precision, dimensions, status, created_by)
                       values (%s, 'Cross-tenant write', 'unknown', 'unknown', '{}'::jsonb, 'draft', %s)""",
                    (org_b, owner_a),
                )
            cursor.execute("rollback to savepoint cross_tenant_write")

            cursor.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(viewer_a),))
            cursor.execute("select title from vernis.evidence_documents order by title")
            assert cursor.fetchall() == [("Tenant A internal",)]
            cursor.execute("savepoint viewer_write")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute(
                    """insert into vernis.artworks
                       (organization_id, title, attribution_status, date_precision, dimensions, status, created_by)
                       values (%s, 'Viewer write', 'unknown', 'unknown', '{}'::jsonb, 'draft', %s)""",
                    (org_a, viewer_a),
                )
            cursor.execute("rollback to savepoint viewer_write")
    finally:
        connection.rollback()
        connection.close()
