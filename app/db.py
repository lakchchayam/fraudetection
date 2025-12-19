from collections.abc import Generator
from contextlib import contextmanager
import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """
    Configuration hook for database URL.

    - In production, set DATABASE_URL to a PostgreSQL URL.
    - For local dev, we default to a SQLite file to avoid needing a running DB.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # Local dev default: SQLite file in project root.
    return "sqlite:///./fraud_dev.db"


database_url = get_database_url()
engine = create_engine(database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Auto-create tables for SQLite dev AND Postgres (simple resume mode).
# In a real enterprise app, we'd use Alembic migrations (e.g. `alembic upgrade head`).
try:
    # Check if we are using SQLite or Postgres
    # For this resume demo, we want tables to be created automatically on Render too.
    from app import models
    models.Base.metadata.create_all(engine)
except Exception:
    # Fail silently or log error
    pass


@contextmanager
def db_session() -> Generator[Session, Any, None]:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


