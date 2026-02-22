"""
scripts/run_ingestion.py — CLI to run the full ingestion pipeline end-to-end.

Usage:
    python scripts/run_ingestion.py
    python scripts/run_ingestion.py --no-ai   # skip AI keyword generation
    python scripts/run_ingestion.py --limit 20
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_ingestion")

from app.config import settings
from app.ingestion.fetcher import fetch_jobs
from app.ingestion.normalizer import normalize_jobs
from app.ingestion.filters import apply_filters
from app.db.session import get_session
from app.db.repository import (
    get_or_create_company,
    job_posting_exists,
    save_job_posting,
)


def run(limit: int, use_ai: bool) -> None:
    print("\n" + "="*55)
    print("  🤖  AI Lead Gen Agent — Ingestion Pipeline")
    print("="*55)

    # ── Step 1: Fetch ─────────────────────────────────────────
    print(f"\n[1/4] 📡 Fetching jobs from RemoteOK (limit={limit})...")
    raw_jobs = fetch_jobs(limit=limit)
    print(f"      ✅ Fetched {len(raw_jobs)} raw job postings.")

    if not raw_jobs:
        print("      ⚠️  No jobs fetched. Exiting.")
        return

    # ── Step 2: Normalize ────────────────────────────────────
    print("\n[2/4] 🧹 Normalizing job data...")
    jobs = normalize_jobs(raw_jobs)
    print(f"      ✅ Normalized {len(jobs)} jobs.")

    # ── Step 3: Filter ────────────────────────────────────────
    ai_label = "AI-powered" if use_ai else "default keyword"
    print(f"\n[3/4] 🔍 Filtering with {ai_label} filter...")
    filtered = apply_filters(jobs, use_ai_keywords=use_ai)
    print(f"      ✅ {len(filtered)} jobs passed the filter.")

    if not filtered:
        print("      ⚠️  No jobs passed the filter. Try adjusting keywords or product description.")
        return

    # ── Step 4: Save to DB ────────────────────────────────────
    print(f"\n[4/4] 💾 Saving new job postings to database...")
    saved = 0
    skipped = 0

    with get_session() as db:
        for job in filtered:
            # Dedup: skip if this URL already exists in DB
            if job.job_url and job_posting_exists(db, job.job_url):
                skipped += 1
                continue

            company = get_or_create_company(db, job)
            save_job_posting(db, job, company)
            saved += 1

    print(f"      ✅ Saved {saved} new postings. Skipped {skipped} duplicates.")

    print("\n" + "="*55)
    print(f"  🎉 Ingestion complete! {saved} new postings ready for AI qualification.")
    print("="*55 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run the ingestion pipeline.")
    parser.add_argument(
        "--limit", type=int, default=settings.max_jobs_per_run,
        help="Max number of jobs to fetch (default from .env)"
    )
    parser.add_argument(
        "--no-ai", action="store_true",
        help="Skip AI keyword generation and use default role keywords"
    )
    args = parser.parse_args()
    run(limit=args.limit, use_ai=not args.no_ai)


if __name__ == "__main__":
    main()
