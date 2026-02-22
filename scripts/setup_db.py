"""
scripts/setup_db.py — Initialize the database schema.

Run once before starting the application for the first time:
    python scripts/setup_db.py

This creates all tables defined in app/db/models.py directly via SQLAlchemy
metadata (no Alembic needed for the initial setup; Alembic is used for future
schema migrations).
"""

import sys
import os

# Ensure the project root is on the path so we can import `app`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import inspect, text

from app.db.session import engine
from app.db.models import Base
from app.config import settings


def setup_db() -> None:
    print("🔌 Connecting to database...")
    print(f"   URL: {settings.database_url[:40]}...")

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Connection successful.")

    print("\n📦 Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)

    # Report which tables were found
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"✅ Tables in database: {tables}")

    print("\n🎉 Database setup complete!")


if __name__ == "__main__":
    setup_db()
