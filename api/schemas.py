"""
api/schemas.py — Pydantic request/response models for all API endpoints.

These are the API contract — separate from DB ORM models so we can
control exactly what data is exposed over HTTP.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.db.models import LeadStatus, DeliveryStatus


# ── Shared ────────────────────────────────────────────────────────────────────

class OKResponse(BaseModel):
    """Generic success acknowledgement."""
    status: str = "ok"
    message: str


# ── Ingestion ─────────────────────────────────────────────────────────────────

class IngestionRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=200, description="Max jobs to fetch")
    use_ai_filter: bool = Field(default=True, description="Use AI keyword generation")


class IngestionResult(BaseModel):
    fetched: int
    normalized: int
    passed_filter: int
    saved: int
    skipped_duplicates: int
    message: str


# ── Company ───────────────────────────────────────────────────────────────────

class CompanyOut(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Job Posting ───────────────────────────────────────────────────────────────

class JobPostingOut(BaseModel):
    id: int
    title: str
    url: Optional[str] = None
    source: Optional[str] = None
    posted_at: Optional[datetime] = None
    is_processed: bool
    company: Optional[CompanyOut] = None

    model_config = {"from_attributes": True}


# ── Lead ─────────────────────────────────────────────────────────────────────

class LeadOut(BaseModel):
    id: int
    status: LeadStatus
    relevance_score: Optional[float] = None
    reason: Optional[str] = None
    contact_role: Optional[str] = None
    company_pain_points: Optional[str] = None
    ai_analysis: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    company: Optional[CompanyOut] = None
    job_posting: Optional[JobPostingOut] = None

    model_config = {"from_attributes": True}


class LeadStatusUpdate(BaseModel):
    status: LeadStatus = Field(..., description="New lead status")


class AiQualificationResult(BaseModel):
    processed: int
    qualified: int
    rejected: int
    message: str


# ── Outreach ──────────────────────────────────────────────────────────────────

class OutreachResult(BaseModel):
    attempted: int
    sent: int
    failed: int
    skipped: int
    message: str


class OutreachEmailOut(BaseModel):
    id: int
    lead_id: int
    to_address: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    delivery_status: DeliveryStatus
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}
