"""
app/config.py — Central configuration loaded from environment variables.
All modules import settings from here; never read os.environ directly elsewhere.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    openrouter_model: str = Field(
        default="openrouter/trinity-large-preview:free",
        description="OpenRouter model identifier",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(..., description="PostgreSQL connection URI")

    # ── Email ─────────────────────────────────────────────────────────────────
    gmail_user: str = Field(..., description="Gmail sender address")
    gmail_app_password: str = Field(..., description="Gmail App Password (16 chars)")

    # ── Product Context ───────────────────────────────────────────────────────
    product_description: str = Field(
        ...,
        description="Description of the product/service the agent is generating leads for",
    )

    # ── Outreach ──────────────────────────────────────────────────────────────
    mailer_dry_run: bool = Field(
        default=True,
        description="If True, print emails to stdout instead of actually sending",
    )
    min_relevance_score: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Minimum lead relevance score (0–100) to be considered qualified",
    )

    # ── Ingestion ─────────────────────────────────────────────────────────────
    max_jobs_per_run: int = Field(
        default=50,
        gt=0,
        description="Max job postings to fetch per ingestion run",
    )


# Singleton — import this everywhere
settings = Settings()
