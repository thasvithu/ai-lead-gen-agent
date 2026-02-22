"""
tests/test_db.py — Unit tests for the repository and database layer.

Uses an in-memory SQLite database (via SQLAlchemy) so no real Supabase
connection is required. Tests run fast and fully in isolation.

NOTE: conftest.py injects dummy env vars before any app module is imported,
preventing pydantic-settings from failing on missing required fields.
"""

import pytest
import sqlalchemy
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Lead, LeadStatus
from app.db.repository import (
    get_or_create_company,
    save_job_posting,
    job_posting_exists,
    get_unprocessed_postings,
    mark_posting_processed,
    create_lead,
    update_lead_status,
    get_leads_for_outreach,
)
from app.ingestion.normalizer import NormalizedJob


# ── In-memory DB Fixture ──────────────────────────────────────────────────────

@pytest.fixture
def db():
    """
    Provide a fresh in-memory SQLite session for each test.

    SQLite doesn't support PostgreSQL native ENUMs, so we temporarily
    set native_enum=False on all Enum columns before creating tables.
    """
    import sqlalchemy as sa

    # Patch: disable native enums for SQLite compatibility
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, sa.Enum):
                col.type.native_enum = False

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        # Restore native_enum so production code is unaffected
        for table in Base.metadata.tables.values():
            for col in table.columns:
                if isinstance(col.type, sa.Enum):
                    col.type.native_enum = True


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_normalized_job(
    company_name="Acme Corp",
    company_domain="acme.com",
    title="Engineering Manager",
    job_url="https://remoteok.com/jobs/001",
    external_id="REMOTEOK-001",
) -> NormalizedJob:
    return NormalizedJob(
        external_id=external_id,
        title=title,
        company_name=company_name,
        company_domain=company_domain,
        company_url=f"https://{company_domain}",
        job_url=job_url,
        description="We are looking for an engineering manager.",
        tags=["engineering", "management"],
        location="Remote",
        posted_at=datetime.now(timezone.utc),
        source="remoteok",
    )


def make_company_and_posting(db, job: NormalizedJob = None):
    """Helper: return (company, posting) for a NormalizedJob."""
    if job is None:
        job = make_normalized_job()
    company = get_or_create_company(db, job)
    posting = save_job_posting(db, job, company)
    return company, posting


# ── get_or_create_company ─────────────────────────────────────────────────────

class TestGetOrCreateCompany:
    def test_creates_new_company(self, db):
        job = make_normalized_job(company_name="TechCorp", company_domain="techcorp.io")
        company = get_or_create_company(db, job)
        assert company.id is not None
        assert company.name == "TechCorp"
        assert company.domain == "techcorp.io"

    def test_returns_existing_company_by_domain(self, db):
        job1 = make_normalized_job(company_name="TechCorp", company_domain="techcorp.io")
        job2 = make_normalized_job(company_name="TechCorp v2", company_domain="techcorp.io")
        c1 = get_or_create_company(db, job1)
        c2 = get_or_create_company(db, job2)
        assert c1.id == c2.id  # Same DB row returned — idempotent

    def test_creates_separate_companies_for_different_domains(self, db):
        job_a = make_normalized_job(company_name="Alpha", company_domain="alpha.com")
        job_b = make_normalized_job(company_name="Beta", company_domain="beta.com")
        c1 = get_or_create_company(db, job_a)
        c2 = get_or_create_company(db, job_b)
        assert c1.id != c2.id


# ── save_job_posting / job_posting_exists ─────────────────────────────────────

class TestJobPosting:
    def test_saves_new_posting(self, db):
        company, posting = make_company_and_posting(db)
        assert posting.id is not None
        assert posting.title == "Engineering Manager"
        assert posting.is_processed is False

    def test_job_posting_exists_returns_true(self, db):
        job = make_normalized_job(job_url="https://remoteok.com/jobs/999")
        company = get_or_create_company(db, job)
        save_job_posting(db, job, company)
        assert job_posting_exists(db, url="https://remoteok.com/jobs/999") is True

    def test_job_posting_exists_returns_false_for_unknown(self, db):
        assert job_posting_exists(db, url="https://remoteok.com/jobs/unknown") is False

    def test_posting_linked_to_company(self, db):
        company, posting = make_company_and_posting(db)
        assert posting.company_id == company.id


# ── get_unprocessed_postings / mark_posting_processed ────────────────────────

class TestProcessingFlow:
    def test_new_posting_appears_in_unprocessed(self, db):
        make_company_and_posting(db)
        results = get_unprocessed_postings(db, limit=10)
        assert len(results) == 1

    def test_mark_processed_removes_from_queue(self, db):
        _, posting = make_company_and_posting(db)
        mark_posting_processed(db, posting.id)
        results = get_unprocessed_postings(db, limit=10)
        assert len(results) == 0

    def test_limit_is_respected(self, db):
        for i in range(5):
            job = make_normalized_job(
                title=f"Job {i}",
                job_url=f"https://remoteok.com/jobs/{i}",
                external_id=f"ID-{i}",
                company_domain=f"company{i}.com",
            )
            company = get_or_create_company(db, job)
            save_job_posting(db, job, company)
        results = get_unprocessed_postings(db, limit=3)
        assert len(results) == 3


# ── create_lead / update_lead_status / get_leads_for_outreach ────────────────

class TestLeads:
    def test_create_lead(self, db):
        company, posting = make_company_and_posting(db)
        lead = create_lead(
            db=db,
            company=company,
            posting=posting,
            relevance_score=82.0,
            ai_analysis='{"raw": "response"}',
            reason="Strong signals.",
            contact_role="Head of Engineering",
            company_pain_points='["slow reviews"]',
        )
        assert lead.id is not None
        assert lead.relevance_score == 82.0
        assert lead.status == LeadStatus.QUALIFIED

    def test_qualified_lead_appears_in_outreach_queue(self, db):
        company, posting = make_company_and_posting(db)
        create_lead(
            db=db, company=company, posting=posting,
            relevance_score=75.0, ai_analysis="{}", reason="Good fit.",
            contact_role="CTO", company_pain_points="[]",
        )
        leads = get_leads_for_outreach(db, limit=10)
        assert len(leads) == 1

    def test_emailed_lead_not_in_outreach_queue(self, db):
        company, posting = make_company_and_posting(db)
        lead = create_lead(
            db=db, company=company, posting=posting,
            relevance_score=75.0, ai_analysis="{}", reason="Good fit.",
            contact_role="CTO", company_pain_points="[]",
        )
        update_lead_status(db, lead.id, LeadStatus.EMAILED)
        leads = get_leads_for_outreach(db, limit=10)
        assert len(leads) == 0

    def test_update_lead_status(self, db):
        company, posting = make_company_and_posting(db)
        lead = create_lead(
            db=db, company=company, posting=posting,
            relevance_score=65.0, ai_analysis="{}", reason="Decent fit.",
            contact_role="VP Engineering", company_pain_points="[]",
        )
        update_lead_status(db, lead.id, LeadStatus.REPLIED)
        db.refresh(lead)
        assert lead.status == LeadStatus.REPLIED
