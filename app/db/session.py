"""
app/db/session.py — SQLAlchemy engine and session factory.

Usage:
    from app.db.session import get_db

    # As a FastAPI dependency:
    def my_route(db: Session = Depends(get_db)):
        ...

    # In scripts:
    with get_session() as db:
        ...
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Create the async-capable engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,          # reconnect on stale connections
    pool_size=5,
    max_overflow=10,
    echo=False,                  # set True to log all SQL (useful for debugging)
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and ensures it's closed."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for use in scripts and services (non-FastAPI code)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
