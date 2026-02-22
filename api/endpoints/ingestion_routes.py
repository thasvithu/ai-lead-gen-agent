"""
api/endpoints/ingestion_routes.py — Routes for triggering and checking ingestion.

POST /ingestion/run   — Fetch + normalize + filter + save job postings
POST /ingestion/qualify — Run AI qualification on unprocessed postings
GET  /ingestion/status  — Count of unprocessed postings in queue
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repository import get_unprocessed_postings
from app.services.lead_service import process_new_postings
from api.schemas import IngestionRequest, IngestionResult, AiQualificationResult

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run", response_model=IngestionResult, summary="Run ingestion pipeline")
def run_ingestion(request: IngestionRequest, db: Session = Depends(get_db)):
    """
    Fetch job postings from RemoteOK, normalize, filter, and save new ones to the database.
    Returns a summary of what was fetched, filtered, and saved.
    """
    try:
        from app.ingestion.fetcher import fetch_jobs
        from app.ingestion.normalizer import normalize_jobs
        from app.ingestion.filters import keyword_filter
        from app.db.repository import job_posting_exists, get_or_create_company, save_job_posting

        # 1. Fetch
        raw_jobs = fetch_jobs(limit=request.limit)
        fetched = len(raw_jobs)

        # 2. Normalize
        normalized = normalize_jobs(raw_jobs)
        norm_count = len(normalized)

        # 3. Filter
        filtered = keyword_filter(normalized)
        filter_count = len(filtered)

        # 4. Save (dedup)
        saved = 0
        skipped = 0
        for job in filtered:
            if job_posting_exists(db, url=job.job_url):
                skipped += 1
                continue
            company = get_or_create_company(db, job)
            save_job_posting(db, job, company)
            saved += 1
        db.commit()

        return IngestionResult(
            fetched=fetched,
            normalized=norm_count,
            passed_filter=filter_count,
            saved=saved,
            skipped_duplicates=skipped,
            message=f"Ingestion complete. {saved} new postings saved.",
        )
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/qualify", response_model=AiQualificationResult, summary="Run AI qualification")
def run_qualification(db: Session = Depends(get_db)):
    """
    Run AI lead qualification on all unprocessed job postings.
    Calls DeepSeek via OpenRouter to score and qualify each posting.
    """
    try:
        result = process_new_postings()
        return AiQualificationResult(
            processed=result.get("processed", 0),
            qualified=result.get("qualified", 0),
            rejected=result.get("rejected", 0),
            message=(
                f"Qualification complete. "
                f"{result.get('qualified', 0)} leads qualified out of "
                f"{result.get('processed', 0)} processed."
            ),
        )
    except Exception as exc:
        logger.error("Qualification failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status", summary="Get ingestion queue size")
def ingestion_status(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return the count of job postings not yet processed by the AI qualification step."""
    unprocessed = get_unprocessed_postings(db, limit=limit)
    return {
        "unprocessed_count": len(unprocessed),
        "message": f"{len(unprocessed)} postings awaiting AI qualification.",
    }
