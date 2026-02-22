"""
app/ingestion/normalizer.py — Cleans and standardizes raw job posting dicts.

Takes raw API responses from fetcher.py and returns clean, typed Pydantic models
ready for storage and AI processing.
"""

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Output schema ────────────────────────────────────────────────────────────

class NormalizedJob(BaseModel):
    """Clean, structured job posting ready for filtering and DB storage."""

    source: str = "remoteok"
    external_id: str                        # original ID from the source
    title: str
    company_name: str
    company_domain: str | None = None       # extracted from company_url
    company_url: str | None = None
    job_url: str | None = None
    location: str | None = None
    description: str                        # plain text, stripped of HTML
    tags: list[str] = Field(default_factory=list)
    posted_at: datetime | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _strip_html(raw: str) -> str:
    """Remove all HTML tags and decode HTML entities."""
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "lxml")
    text = soup.get_text(separator=" ")
    # Collapse extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_domain(url: str | None) -> str | None:
    """Extract bare domain from a URL, e.g. 'https://acme.com/about' → 'acme.com'."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Strip 'www.'
        if domain.startswith("www."):
            domain = domain[4:]
        return domain or None
    except Exception:
        return None


def _parse_date(value: Any) -> datetime | None:
    """Parse an epoch timestamp or ISO string into a datetime."""
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value)
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _normalize_title(title: str) -> str:
    """Capitalize words and strip excess whitespace."""
    return " ".join(word.capitalize() for word in title.strip().split()) if title else ""


# ── Main function ────────────────────────────────────────────────────────────

def normalize_job(raw: dict[str, Any]) -> NormalizedJob | None:
    """
    Normalize a single raw job dict from RemoteOK into a NormalizedJob.

    Returns None if the job is missing critical fields (title or company).
    """
    try:
        title = _normalize_title(raw.get("position") or raw.get("title") or "")
        company_name = (raw.get("company") or "").strip()

        if not title or not company_name:
            logger.debug("Skipping job %s — missing title or company.", raw.get("id"))
            return None

        company_url = raw.get("company_logo") or raw.get("url") or None
        # RemoteOK puts the apply URL in 'url' and company logo URL in 'company_logo'
        # The job application URL is in 'apply_url' or 'url'
        job_url = raw.get("apply_url") or raw.get("url") or None
        company_domain = _extract_domain(raw.get("company_logo"))

        description_raw = raw.get("description") or raw.get("tags_description") or ""
        description = _strip_html(description_raw)
        if not description:
            # Fallback: use tags as a minimal description context
            tags = raw.get("tags") or []
            description = f"Role: {title} at {company_name}. Tags: {', '.join(tags)}"

        return NormalizedJob(
            source="remoteok",
            external_id=str(raw.get("id", "")),
            title=title,
            company_name=company_name,
            company_domain=company_domain,
            company_url=company_url,
            job_url=job_url,
            location=raw.get("location") or "Remote",
            description=description[:4000],  # cap to avoid LLM context issues
            tags=[t.lower() for t in (raw.get("tags") or [])],
            posted_at=_parse_date(raw.get("date") or raw.get("epoch")),
        )

    except Exception as e:
        logger.warning("Failed to normalize job %s: %s", raw.get("id"), e)
        return None


def normalize_jobs(raw_jobs: list[dict[str, Any]]) -> list[NormalizedJob]:
    """Normalize a batch of raw job dicts. Skips invalid entries."""
    results = []
    for raw in raw_jobs:
        job = normalize_job(raw)
        if job:
            results.append(job)

    logger.info("Normalized %d / %d jobs successfully.", len(results), len(raw_jobs))
    return results
