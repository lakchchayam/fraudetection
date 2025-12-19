import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from app import models


@pytest.fixture(scope="session")
def engine() -> Generator:
    # Use in-memory SQLite for tests; schema should be portable.
    test_db_url = "sqlite+pysqlite:///:memory:"
    engine = create_engine(test_db_url, future=True)
    models.Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    session: Session = TestingSessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """
    FastAPI TestClient with a DB session injected via dependency override.
    """
    app = create_app()

    # Simple dependency override pattern: monkeypatch app.db.SessionLocal if needed.
    # To avoid complex wiring, we'll store the session on app.state in tests.
    app.state._test_session = db_session

    client = TestClient(app)
    return client



