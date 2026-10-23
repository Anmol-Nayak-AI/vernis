"""Read-only summary of the Vernis schema and its row-level-security posture."""

from sqlalchemy import inspect, text

from app.config import settings
from app.db.session import engine


def main() -> None:
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names(schema=settings.database_schema))
    print(f"schema={settings.database_schema}")
    print(f"tables={','.join(tables) if tables else '(none)'}")
    if engine.dialect.name != "postgresql" or not tables:
        return
    with engine.connect() as connection:
        revision = connection.scalar(text("select version_num from alembic_version"))
        print(f"alembic_revision={revision or '(none)'}")
        rows = connection.execute(
            text(
                """select c.relname, c.relrowsecurity, c.relforcerowsecurity
                   from pg_class c
                   join pg_namespace n on n.oid = c.relnamespace
                   where n.nspname = :schema and c.relkind = 'r'
                   order by c.relname"""
            ),
            {"schema": settings.database_schema},
        )
        for table, rls, forced in rows:
            print(f"table={table} rls={str(rls).lower()} force_rls={str(forced).lower()}")


if __name__ == "__main__":
    main()
