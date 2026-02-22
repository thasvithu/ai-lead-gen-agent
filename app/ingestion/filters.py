"""
app/ingestion/filters.py — Two-stage filtering of normalized job postings.

Stage 1 (fast): keyword pre-filter — checks job title/tags against a keyword list.
Stage 2 (deep): uses the AI engine to generate domain-specific keywords
                matching the user's product description.

The keyword list is generated once per run by the LLM and cached in memory.
"""

import logging
from functools import lru_cache

from app.ingestion.normalizer import NormalizedJob
from app.config import settings

logger = logging.getLogger(__name__)


# ── Stage 1: fast keyword filter ─────────────────────────────────────────────

# Default broad "buyer signal" roles — used as fallback if AI keyword gen fails
DEFAULT_BUYER_ROLES = [
    "cto", "vp engineering", "head of engineering", "engineering manager",
    "director of engineering", "chief technology officer",
    "founder", "co-founder", "ceo",
    "vp product", "head of product", "product manager", "product lead",
    "vp operations", "head of operations", "operations manager",
    "devops", "platform engineer", "staff engineer", "principal engineer",
    "data engineer", "ml engineer", "machine learning",
]


def _job_text(job: NormalizedJob) -> str:
    """Combine all searchable text fields into one lowercase string."""
    parts = [
        job.title,
        job.company_name,
        " ".join(job.tags),
        job.description[:500],   # only first 500 chars for speed
    ]
    return " ".join(p for p in parts if p).lower()


def keyword_filter(
    jobs: list[NormalizedJob],
    keywords: list[str] | None = None,
) -> list[NormalizedJob]:
    """
    Stage 1: fast keyword pre-filter.

    Keeps only jobs where the title, tags, or first 500 chars of description
    contain at least one of the given keywords.

    Args:
        jobs:     Normalized job list.
        keywords: List of lowercase keywords to match against. Falls back to
                  DEFAULT_BUYER_ROLES if not provided.

    Returns:
        Filtered list of NormalizedJob.
    """
    kw_list = [k.lower() for k in (keywords or DEFAULT_BUYER_ROLES)]
    passed = []

    for job in jobs:
        text = _job_text(job)
        if any(kw in text for kw in kw_list):
            passed.append(job)

    logger.info(
        "Keyword filter: %d / %d jobs passed (keywords=%s).",
        len(passed), len(jobs), kw_list[:5],
    )
    return passed


# ── Stage 2: AI-powered keyword generation ────────────────────────────────────

@lru_cache(maxsize=1)
def get_ai_keywords() -> list[str]:
    """
    Call the AI engine to generate role keywords relevant to the configured
    product description. Result is cached for the lifetime of the process.

    Returns DEFAULT_BUYER_ROLES on failure.
    """
    try:
        # Lazy import to avoid circular imports and allow Stage 1 to run standalone
        from app.ai_engine.processor import generate_keywords
        keywords = generate_keywords(settings.product_description)
        logger.info("AI-generated keywords: %s", keywords)
        return keywords
    except Exception as e:
        logger.warning("AI keyword generation failed, using defaults: %s", e)
        return DEFAULT_BUYER_ROLES


def ai_keyword_filter(jobs: list[NormalizedJob]) -> list[NormalizedJob]:
    """
    Stage 2: filter using AI-generated role keywords.
    Calls get_ai_keywords() (cached) then delegates to keyword_filter().
    """
    keywords = get_ai_keywords()
    return keyword_filter(jobs, keywords=keywords)


# ── Combined pipeline ─────────────────────────────────────────────────────────

def apply_filters(jobs: list[NormalizedJob], use_ai_keywords: bool = True) -> list[NormalizedJob]:
    """
    Full two-stage filter pipeline.

    Args:
        jobs:            Normalized job list.
        use_ai_keywords: If True, generates keywords via LLM. If False, uses defaults.

    Returns:
        Filtered list of NormalizedJob that passed both stages.
    """
    if use_ai_keywords:
        return ai_keyword_filter(jobs)
    return keyword_filter(jobs)
