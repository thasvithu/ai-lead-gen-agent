"""
app/services/scoring.py — Lead relevance scoring logic.

Applies a configurable threshold on the AI's relevance_score to decide
if a lead should be persisted as qualified.
"""

import logging

from app.config import settings
from app.ai_engine.processor import QualificationResult

logger = logging.getLogger(__name__)


def is_lead_qualified(result: QualificationResult) -> bool:
    """
    Determine if a lead passes our qualification threshold.

    A lead is qualified if BOTH:
      1. The LLM explicitly flagged it as is_qualified=True
      2. The relevance_score meets or exceeds the configured MIN_RELEVANCE_SCORE

    Args:
        result: The QualificationResult from the AI engine.

    Returns:
        True if the lead should be saved and outreached.
    """
    passes_score = result.relevance_score >= settings.min_relevance_score
    passes_flag = result.is_qualified

    if not passes_flag:
        logger.debug("Lead rejected — LLM flagged as not qualified.")
    elif not passes_score:
        logger.debug(
            "Lead rejected — score %.1f below threshold %d.",
            result.relevance_score, settings.min_relevance_score,
        )
    else:
        logger.debug(
            "Lead qualified — score=%.1f, threshold=%d.",
            result.relevance_score, settings.min_relevance_score,
        )

    return passes_flag and passes_score
