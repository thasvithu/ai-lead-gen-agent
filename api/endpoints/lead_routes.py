"""
api/endpoints/lead_routes.py — CRUD routes for leads.

GET    /leads              — List leads (filterable by status)
GET    /leads/{id}         — Get a single lead with full detail
PATCH  /leads/{id}/status  — Update lead status manually
GET    /leads/stats        — Aggregate counts by status
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Lead, LeadStatus
from app.db.repository import get_leads_by_status, update_lead_status
from api.schemas import LeadOut, LeadStatusUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[LeadOut], summary="List leads")
def list_leads(
    status: Optional[LeadStatus] = Query(
        default=None,
        description="Filter by status. Omit to return all leads.",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Return a list of leads, optionally filtered by status.
    Leads include company and job posting details.
    """
    if status:
        leads = get_leads_by_status(db, status=status, limit=limit)
    else:
        leads = (
            db.query(Lead)
            .order_by(Lead.created_at.desc())
            .limit(limit)
            .all()
        )
    return leads


@router.get("/stats", summary="Lead counts by status")
def lead_stats(db: Session = Depends(get_db)):
    """Return aggregate lead counts grouped by status."""
    stats = {}
    for status in LeadStatus:
        count = db.query(Lead).filter(Lead.status == status).count()
        stats[status.value] = count
    stats["total"] = sum(stats.values())
    return stats


@router.get("/{lead_id}", response_model=LeadOut, summary="Get lead by ID")
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Fetch a single lead by its database ID, including company and job posting."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")
    return lead


@router.patch("/{lead_id}/status", response_model=LeadOut, summary="Update lead status")
def patch_lead_status(
    lead_id: int,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Manually update the status of a lead.
    Valid statuses: new, qualified, emailed, replied, rejected.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found.")
    update_lead_status(db, lead_id, payload.status)
    db.commit()
    db.refresh(lead)
    logger.info("Lead %d status updated to %s via API.", lead_id, payload.status)
    return lead
