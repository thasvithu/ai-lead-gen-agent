"""
app/db/models.py — SQLAlchemy ORM models for the lead generation system.

Tables:
  - Company       → a potential customer company
  - JobPosting    → a job post fetched from a job board, linked to a Company
  - Lead          → a qualified lead produced from a JobPosting
  - OutreachEmail → an email sent (or queued) for a Lead
"""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ── Base ─────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Enums ────────────────────────────────────────────────────────────────────

class LeadStatus(str, enum.Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    EMAILED = "emailed"
    REPLIED = "replied"
    REJECTED = "rejected"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# ── Models ───────────────────────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True, unique=True)
    location = Column(String(255), nullable=True)
    website = Column(String(512), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    job_postings = relationship("JobPosting", back_populates="company", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name!r}>"


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(1024), nullable=True, unique=True)
    source = Column(String(100), nullable=False, default="remoteok")  # e.g. "remoteok"
    posted_at = Column(DateTime, nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    company = relationship("Company", back_populates="job_postings")
    lead = relationship("Lead", back_populates="job_posting", uselist=False)

    def __repr__(self) -> str:
        return f"<JobPosting id={self.id} title={self.title!r}>"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True)

    status = Column(Enum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    relevance_score = Column(Float, nullable=True)        # 0.0 – 100.0
    ai_analysis = Column(Text, nullable=True)             # Raw LLM qualification JSON
    reason = Column(Text, nullable=True)                  # Human-readable qualification reason
    contact_role = Column(String(255), nullable=True)     # e.g. "CTO", "Head of Engineering"
    company_pain_points = Column(Text, nullable=True)     # JSON list stored as text

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    company = relationship("Company", back_populates="leads")
    job_posting = relationship("JobPosting", back_populates="lead")
    outreach_emails = relationship("OutreachEmail", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Lead id={self.id} status={self.status} score={self.relevance_score}>"


class OutreachEmail(Base):
    __tablename__ = "outreach_emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    to_address = Column(String(255), nullable=True)       # may be unknown initially
    subject = Column(String(512), nullable=False)
    body = Column(Text, nullable=False)
    delivery_status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="outreach_emails")

    def __repr__(self) -> str:
        return f"<OutreachEmail id={self.id} lead_id={self.lead_id} status={self.delivery_status}>"
