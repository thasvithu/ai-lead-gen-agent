"""
app/ingestion/fetcher.py — Fetches raw job postings from external job boards.

Primary source: RemoteOK public API (free, no auth required).
  Docs: https://remoteok.com/api

Returns a list of raw job dicts for downstream normalization.
"""

import logging
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

REMOTEOK_API_URL = "https://remoteok.com/api"

# RemoteOK requires a real User-Agent or it returns 403
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AILeadGenBot/1.0; +https://github.com/your-repo)"
}


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _fetch_remoteok_raw(tags: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Internal: calls RemoteOK API with optional tag filter.
    Retries up to 3 times on transient network errors.
    """
    params = {}
    if tags:
        # RemoteOK accepts comma-separated tags via the 'tags' query param
        params["tags"] = ",".join(tags)

    response = requests.get(
        REMOTEOK_API_URL,
        headers=HEADERS,
        params=params,
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()

    # RemoteOK always returns a legal notice dict as the first element — skip it
    jobs = [item for item in data if isinstance(item, dict) and "id" in item]
    return jobs


def fetch_jobs(tags: list[str] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    """
    Fetch job postings from RemoteOK.

    Args:
        tags:  Optional list of role/tech tags to filter by (e.g. ["engineer", "cto"]).
               If None, fetches all remote jobs.
        limit: Max number of jobs to return. Defaults to settings.max_jobs_per_run.

    Returns:
        List of raw job dicts from the API.
    """
    if limit is None:
        limit = settings.max_jobs_per_run

    logger.info("Fetching jobs from RemoteOK (tags=%s, limit=%d)...", tags, limit)

    try:
        jobs = _fetch_remoteok_raw(tags=tags)
    except requests.RequestException as e:
        logger.error("Failed to fetch jobs from RemoteOK after retries: %s", e)
        return []

    # Apply limit
    jobs = jobs[:limit]

    logger.info("Fetched %d job postings from RemoteOK.", len(jobs))
    return jobs
