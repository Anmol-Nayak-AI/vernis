from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.router import router  # noqa: F401
from app.config import settings
from app.core.security import RequestPrincipal, get_request_principal
from app.db.session import Base, get_db
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {settings.database_schema: None}},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def principal_state() -> dict[str, RequestPrincipal]:
    return {
        "current": RequestPrincipal(
            user_id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
            email="owner@example.test",
        )
    }


@pytest.fixture()
def client(db_session: Session, principal_state: dict[str, RequestPrincipal], tmp_path) -> Generator[TestClient, None, None]:
    def override_db():
        yield db_session

    def override_principal():
        return principal_state["current"]

    previous_storage_root = settings.storage_root
    settings.storage_root = str(tmp_path / "storage")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_request_principal] = override_principal
    with TestClient(app) as test_client:
        yield test_client
    settings.storage_root = previous_storage_root
    app.dependency_overrides.clear()
