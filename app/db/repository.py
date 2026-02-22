"""
app/db/repository.py — All database read/write operations.

Business logic should never write raw SQL or ORM queries directly —
everything goes through this module. This keeps DB logic centralized
and easy to test/mock.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Company, DeliveryStatus, JobPosting, Lead, LeadStatus, OutreachEmail
from app.ingestion.normalizer import NormalizedJob

logger = logging.getLogger(__name__)


# ── Company ───────────────────────────────────────────────────────────────────

def get_or_create_company(db: Session, job: NormalizedJob) -> Company:
    """
    Find an existing Company by domain (or name as fallback), or create a new one.
    Returns the Company ORM object.
    """
    company = None

    # Try matching by domain first (most reliable)
    if job.company_domain:
        company = db.query(Company).filter(Company.domain == job.company_domain).first()

    # Fallback: match by exact name
    if not company:
        company = db.query(Company).filter(Company.name == job.company_name).first()

    if not company:
        company = Company(
            name=job.company_name,
            domain=job.company_domain,
            website=job.company_url,
            location=job.location,
        )
        db.add(company)
        db.flush()  # get the ID without committing
        logger.debug("Created new company: %s", company.name)

    return company


# ── Job Posting ───────────────────────────────────────────────────────────────

def job_posting_exists(db: Session, url: str) -> bool:
    """Check if a job posting with this URL already exists (dedup check)."""
    return db.query(JobPosting).filter(JobPosting.url == url).first() is not None


def save_job_posting(db: Session, job: NormalizedJob, company: Company) -> JobPosting:
    """
    Persist a NormalizedJob to the job_postings table.
    Assumes dedup check (job_posting_exists) has already been done.
    """
    posting = JobPosting(
        company_id=company.id,
        title=job.title,
        description=job.description,
        url=job.job_url,
        source=job.source,
        posted_at=job.posted_at,
        is_processed=False,
    )
    db.add(posting)
    db.flush()
    logger.debug("Saved job posting: %s @ %s", posting.title, company.name)
    return posting


def get_unprocessed_postings(db: Session, limit: int = 50) -> list[JobPosting]:
    """Return job postings that haven't been through AI qualification yet."""
    return (
        db.query(JobPosting)
        .filter(JobPosting.is_processed == False)  # noqa: E712
        .order_by(JobPosting.created_at.asc())
        .limit(limit)
        .all()
    )


def mark_posting_processed(db: Session, posting_id: int) -> None:
    """Mark a job posting as processed (AI ran on it)."""
    db.query(JobPosting).filter(JobPosting.id == posting_id).update(
        {"is_processed": True}
    )


# ── Lead ─────────────────────────────────────────────────────────────────────

def create_lead(
    db: Session,
    company: Company,
    posting: JobPosting,
    relevance_score: float,
    ai_analysis: str,
    reason: str,
    contact_role: str,
    company_pain_points: str,  # JSON string
) -> Lead:
    """Create and persist a new qualified Lead."""
    lead = Lead(
        company_id=company.id,
        job_posting_id=posting.id,
        status=LeadStatus.QUALIFIED,
        relevance_score=relevance_score,
        ai_analysis=ai_analysis,
        reason=reason,
        contact_role=contact_role,
        company_pain_points=company_pain_points,
    )
    db.add(lead)
    db.flush()
    logger.info(
        "Lead created: %s @ %s (score=%.1f)",
        posting.title, company.name, relevance_score,
    )
    return lead


def get_leads_by_status(db: Session, status: LeadStatus, limit: int = 50) -> list[Lead]:
    """Fetch leads filtered by status."""
    return (
        db.query(Lead)
        .filter(Lead.status == status)
        .order_by(Lead.created_at.asc())
        .limit(limit)
        .all()
    )


def update_lead_status(db: Session, lead_id: int, status: LeadStatus) -> None:
    """Update the status of a lead."""
    db.query(Lead).filter(Lead.id == lead_id).update({"status": status})
    logger.debug("Lead %d status → %s", lead_id, status)


def get_leads_for_outreach(db: Session, limit: int = 20) -> list[Lead]:
    """Return qualified leads that haven't been emailed yet."""
    return get_leads_by_status(db, LeadStatus.QUALIFIED, limit=limit)


# ── Outreach Email ────────────────────────────────────────────────────────────

def log_outreach_email(
    db: Session,
    lead_id: int,
    subject: str,
    body: str,
    to_address: Optional[str] = None,
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING,
    error_message: Optional[str] = None,
) -> OutreachEmail:
    """Create an OutreachEmail record (called before and after sending)."""
    email = OutreachEmail(
        lead_id=lead_id,
        to_address=to_address,
        subject=subject,
        body=body,
        delivery_status=delivery_status,
        error_message=error_message,
        sent_at=datetime.utcnow() if delivery_status == DeliveryStatus.SENT else None,
    )
    db.add(email)
    db.flush()
    return email


def update_email_delivery_status(
    db: Session,
    email_id: int,
    status: DeliveryStatus,
    error_message: Optional[str] = None,
) -> None:
    """Update delivery status after a send attempt."""
    update_data: dict = {"delivery_status": status}
    if status == DeliveryStatus.SENT:
        update_data["sent_at"] = datetime.utcnow()
    if error_message:
        update_data["error_message"] = error_message
    db.query(OutreachEmail).filter(OutreachEmail.id == email_id).update(update_data)
