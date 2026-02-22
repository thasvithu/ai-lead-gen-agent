"""
tests/conftest.py — Shared pytest configuration and fixtures.

Sets dummy environment variables BEFORE any app module is imported,
so that pydantic-settings doesn't fail on missing required fields.
"""

import os
import pytest

# ── Set dummy env vars before any app module is imported ─────────────────────
# This runs at collection time, before tests execute.
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_MODEL", "test-model")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("GMAIL_USER", "test@example.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "test-password")
os.environ.setdefault("PRODUCT_DESCRIPTION", "A test product for unit tests.")
