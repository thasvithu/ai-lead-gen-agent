"""
api/endpoints/outreach_routes.py — Routes for email outreach.

POST /outreach/run            — Run outreach for all qualified leads
POST /outreach/{lead_id}      — Send outreach for a specific lead
GET  /outreach/history         — List all email send attempts
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Lead, LeadStatus, OutreachEmail
from app.db.repository import get_leads_for_outreach, update_lead_status
from app.config import settings
from app.ai_engine.processor import draft_email
from app.outreach.templates import render_email
from app.outreach.mailer import GmailMailer
from api.schemas import OutreachResult, OutreachEmailOut

logger = logging.getLogger(__name__)
router = APIRouter()


def _send_for_lead(lead: Lead, mailer: GmailMailer, db: Session) -> bool:
    """Draft, render, and send (or dry-run) an email for a single lead."""
    company = lead.company
    posting = lead.job_posting

    try:
        draft = draft_email(
            company_name=company.name if company else "Unknown",
            job_title=posting.title if posting else "Unknown",
            job_description=(posting.description[:800] if posting else ""),
            contact_role=lead.contact_role or "Engineering Leader",
            company_pain_points=lead.company_pain_points or "[]",
            reason=lead.reason or "",
            product_description=settings.product_description,
        )
    except Exception as exc:
        logger.error("LLM draft failed for lead %d: %s", lead.id, exc)
        return False

    rendered = render_email(
        subject=draft.subject,
        plain_body=draft.body,
        sender_name=settings.gmail_user.split("@")[0].capitalize(),
    )

    # In dry-run use sender's own address; real sends need contact discovery
    to_address = settings.gmail_user if settings.mailer_dry_run else None
    if not to_address:
        logger.warning("No recipient address for lead %d — skipping.", lead.id)
        return False

    success = mailer.send(db=db, lead_id=lead.id, to_address=to_address, email=rendered)
    if success:
        update_lead_status(db, lead.id, LeadStatus.EMAILED)
        db.commit()
    return success


@router.post("/run", response_model=OutreachResult, summary="Run outreach for all qualified leads")
def run_outreach(
    limit: int = Query(default=20, ge=1, le=100),
    dry_run: bool = Query(default=True, description="Print emails instead of sending"),
    db: Session = Depends(get_db),
):
    """
    Fetch all qualified-but-not-emailed leads, generate personalized emails
    via AI, and send them (or print in dry-run mode).
    """
    mailer = GmailMailer(dry_run=dry_run)
    leads = get_leads_for_outreach(db, limit=limit)

    if not leads:
        return OutreachResult(
            attempted=0, sent=0, failed=0, skipped=0,
            message="No qualified leads pending outreach.",
        )

    attempted = sent = failed = skipped = 0
    for lead in leads:
        attempted += 1
        success = _send_for_lead(lead, mailer, db)
        if success:
            sent += 1
        else:
            failed += 1

    return OutreachResult(
        attempted=attempted,
        sent=sent,
        failed=failed,
        skipped=skipped,
        message=f"Outreach complete. {sent} emails {'printed' if dry_run else 'sent'}.",
    )


@router.post("/{lead_id}", response_model=OutreachResult, summary="Send outreach for one lead")
def outreach_single_lead(
    lead_id: int,
    dry_run: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    """Generate and send (or dry-run) an outreach email for a specific lead by ID."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")
    if lead.status != LeadStatus.QUALIFIED:
        raise HTTPException(
            status_code=400,
            detail=f"Lead {lead_id} has status '{lead.status.value}' — only QUALIFIED leads can be emailed.",
        )
    mailer = GmailMailer(dry_run=dry_run)
    success = _send_for_lead(lead, mailer, db)
    return OutreachResult(
        attempted=1,
        sent=1 if success else 0,
        failed=0 if success else 1,
        skipped=0,
        message=f"Email {'sent' if success else 'failed'} for lead {lead_id}.",
    )


@router.get("/history", response_model=list[OutreachEmailOut], summary="Outreach email history")
def outreach_history(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return all outreach email records (sent, failed, pending), most recent first."""
    emails = (
        db.query(OutreachEmail)
        .order_by(OutreachEmail.id.desc())
        .limit(limit)
        .all()
    )
    return emails
