from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.db.models import (  # noqa: F401
    Artwork,
    ArtworkAsset,
    AuditEvent,
    Job,
    Organization,
    OrganizationMembership,
    UploadIntent,
    User,
)
from app.db.session import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# These PostgreSQL-specific expression/access-method indexes are created with
# explicit SQL in reviewed migrations. They are not portable ORM metadata and
# must not be interpreted as schema drift by Alembic autogeneration.
MIGRATION_MANAGED_INDEXES = {
    "ix_embeddings_hnsw_cosine",
    "ix_evidence_chunks_hnsw_cosine",
    "ix_evidence_documents_fts",
}


def include_object(_object, name: str | None, type_: str, _reflected: bool, _compare_to) -> bool:
    return not (type_ == "index" and name in MIGRATION_MANAGED_INDEXES)


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
