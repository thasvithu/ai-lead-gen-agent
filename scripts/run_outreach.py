"""
scripts/run_outreach.py — CLI to run the email outreach pipeline.

Steps:
  1. Fetch qualified-but-not-emailed leads from DB
  2. Generate a personalized cold email via LLM (draft_email chain)
  3. Render the email into HTML + plain-text
  4. Send via Gmail SMTP (or print if MAILER_DRY_RUN=true)
  5. Update lead status to EMAILED and log delivery in DB

Usage:
    python scripts/run_outreach.py [--limit N] [--dry-run] [--no-dry-run]
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Imports ───────────────────────────────────────────────────────────────────

from app.config import settings
from app.db.session import get_session
from app.db.repository import (
    get_leads_for_outreach,
    update_lead_status,
)
from app.db.models import LeadStatus
from app.ai_engine.processor import draft_email
from app.outreach.templates import render_email
from app.outreach.mailer import GmailMailer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_lead_context(lead) -> dict:
    """Extract a readable context dict from a Lead ORM object."""
    company = lead.company
    posting = lead.job_posting
    return {
        "company_name": company.name if company else "Unknown",
        "job_title": posting.title if posting else "Unknown",
        "job_description": (posting.description[:800] if posting else ""),
        "company_domain": company.domain if company else "",
        "contact_role": lead.contact_role or "Engineering Leader",
        "company_pain_points": lead.company_pain_points or "[]",
        "reason": lead.reason or "",
    }


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_outreach(limit: int, dry_run: bool) -> dict:
    """
    Run the full outreach pipeline for all pending qualified leads.

    Returns a summary dict: {attempted, sent, failed, skipped}.
    """
    mailer = GmailMailer(dry_run=dry_run)
    summary = {"attempted": 0, "sent": 0, "failed": 0, "skipped": 0}

    with get_session() as db:
        leads = get_leads_for_outreach(db, limit=limit)

        if not leads:
            logger.info("No qualified leads pending outreach.")
            return summary

        logger.info("Found %d leads to contact.", len(leads))

        for lead in leads:
            summary["attempted"] += 1
            company = lead.company
            company_name = company.name if company else "Unknown"

            # Determine recipient email — use company domain as fallback hint
            to_address = _resolve_to_address(lead)
            if not to_address:
                logger.warning(
                    "No email address for lead %d (%s) — skipping.",
                    lead.id, company_name,
                )
                summary["skipped"] += 1
                continue

            logger.info(
                "Processing lead %d — %s @ %s",
                lead.id, lead.contact_role, company_name,
            )

            # 1. Generate personalized email via LLM
            try:
                context = _build_lead_context(lead)
                draft = draft_email(
                    company_name=context["company_name"],
                    job_title=context["job_title"],
                    job_description=context["job_description"],
                    contact_role=context["contact_role"],
                    company_pain_points=context["company_pain_points"],
                    reason=context["reason"],
                    product_description=settings.product_description,
                )
            except Exception as exc:
                logger.error("LLM draft failed for lead %d: %s", lead.id, exc)
                summary["failed"] += 1
                continue

            # 2. Render email
            rendered = render_email(
                subject=draft.subject,
                plain_body=draft.body,
                sender_name=settings.gmail_user.split("@")[0].capitalize(),
            )

            # 3. Send (or dry-run print)
            success = mailer.send(
                db=db,
                lead_id=lead.id,
                to_address=to_address,
                email=rendered,
            )

            # 4. Update lead status
            if success:
                update_lead_status(db, lead.id, LeadStatus.EMAILED)
                db.commit()
                summary["sent"] += 1
            else:
                summary["failed"] += 1

    return summary


def _resolve_to_address(lead) -> str | None:
    """
    Determine the email recipient address for a lead.

    For now we fall back to the gmail_user (self-send in dry-run),
    since we don't yet have contact emails scraped. In production
    this would use a contact discovery service (Apollo, Hunter, etc.)
    """
    # If we stored a contact email on the lead in the future, use it.
    # For now: dry-run sends to self, real sends require a contact email.
    if settings.mailer_dry_run:
        return settings.gmail_user  # Loop-back for demo/testing
    return None  # Block real sends until contact discovery is implemented


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI Lead Gen — Outreach Pipeline")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max number of leads to email per run (default: 20)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="Print emails to stdout instead of sending (overrides .env)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Force real send even if MAILER_DRY_RUN=true in .env",
    )
    args = parser.parse_args()

    # Resolve dry_run flag: CLI flag > .env setting
    if args.dry_run:
        dry_run = True
    elif args.no_dry_run:
        dry_run = False
    else:
        dry_run = settings.mailer_dry_run

    print("\n" + "=" * 55)
    print("  🤖  AI Lead Gen Agent — Outreach Pipeline")
    if dry_run:
        print("  ⚠️   DRY RUN MODE — no emails will be sent")
    print("=" * 55 + "\n")

    result = run_outreach(limit=args.limit, dry_run=dry_run)

    print("\n" + "=" * 55)
    print("  ✅  Outreach complete!")
    print(f"     Attempted : {result['attempted']}")
    print(f"     Sent      : {result['sent']}")
    print(f"     Failed    : {result['failed']}")
    print(f"     Skipped   : {result['skipped']}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
