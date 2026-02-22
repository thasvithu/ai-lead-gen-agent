"""
app/services/lead_service.py — Business logic orchestrating the full
ingestion → AI qualification → DB persistence pipeline.

This is the "glue" layer that coordinates:
  - Fetching unprocessed job postings from the DB
  - Running AI qualification on each
  - Saving qualified leads
  - Marking postings as processed
"""

import json
import logging

from app.config import settings
from app.db.models import JobPosting
from app.db.repository import (
    create_lead,
    get_leads_for_outreach,
    get_unprocessed_postings,
    mark_posting_processed,
    update_lead_status,
)
from app.db.models import LeadStatus
from app.db.session import get_session
from app.ai_engine.processor import qualify_lead
from app.services.scoring import is_lead_qualified

logger = logging.getLogger(__name__)


def process_new_postings(limit: int = 20) -> dict:
    """
    Fetch unprocessed job postings, run AI qualification, and persist qualified leads.

    Args:
        limit: Max postings to process in one call.

    Returns:
        A summary dict: {"processed": int, "qualified": int, "rejected": int}
    """
    stats = {"processed": 0, "qualified": 0, "rejected": 0}

    with get_session() as db:
        postings: list[JobPosting] = get_unprocessed_postings(db, limit=limit)

        if not postings:
            logger.info("No unprocessed job postings found.")
            return stats

        logger.info("Processing %d job postings through AI qualification...", len(postings))

        for posting in postings:
            try:
                result = qualify_lead(
                    company_name=posting.company.name,
                    job_title=posting.title,
                    job_description=posting.description or "",
                    location=posting.company.location or "Remote",
                    product_description=settings.product_description,
                )

                # Mark posting as processed regardless of qualification outcome
                mark_posting_processed(db, posting.id)
                stats["processed"] += 1

                if is_lead_qualified(result):
                    create_lead(
                        db=db,
                        company=posting.company,
                        posting=posting,
                        relevance_score=result.relevance_score,
                        ai_analysis=result.raw_response,
                        reason=result.reason,
                        contact_role=result.target_contact_role,
                        company_pain_points=json.dumps(result.company_pain_points),
                    )
                    stats["qualified"] += 1
                    logger.info(
                        "✅ Qualified: %s @ %s (score=%.1f)",
                        posting.title, posting.company.name, result.relevance_score,
                    )
                else:
                    stats["rejected"] += 1
                    logger.info(
                        "❌ Rejected: %s @ %s (score=%.1f)",
                        posting.title, posting.company.name, result.relevance_score,
                    )

            except Exception as e:
                logger.error(
                    "Error processing posting %d (%s): %s",
                    posting.id, posting.title, e,
                )
                # Don't mark as processed so it can be retried
                stats["rejected"] += 1

    logger.info("Qualification done: %s", stats)
    return stats


def get_qualified_leads_for_outreach(limit: int = 20) -> list:
    """Return qualified leads that haven't been emailed yet."""
    with get_session() as db:
        return get_leads_for_outreach(db, limit=limit)


def mark_lead_as_emailed(lead_id: int) -> None:
    """Update a lead's status to EMAILED after successful outreach."""
    with get_session() as db:
        update_lead_status(db, lead_id, LeadStatus.EMAILED)
