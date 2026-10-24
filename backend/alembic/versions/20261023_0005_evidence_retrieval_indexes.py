"""Hybrid evidence retrieval indexes.

Revision ID: 20261023_0005
Revises: e7d142515352
Create Date: 2026-10-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261023_0005"
down_revision: str | None = "e7d142515352"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "create index ix_evidence_chunks_hnsw_cosine on vernis.evidence_chunks "
        "using hnsw (embedding vector_cosine_ops) where embedding is not null"
    )
    op.execute(
        "create index ix_evidence_documents_fts on vernis.evidence_documents using gin "
        "(to_tsvector('simple'::regconfig, coalesce(title, '') || ' ' || coalesce(extracted_text, '')))"
    )


def downgrade() -> None:
    op.execute("drop index if exists vernis.ix_evidence_documents_fts")
    op.execute("drop index if exists vernis.ix_evidence_chunks_hnsw_cosine")
