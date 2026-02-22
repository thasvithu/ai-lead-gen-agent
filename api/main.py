"""
api/main.py — FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import engine
from app.db.models import Base


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    # Verify DB is reachable on startup
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    print("✅ Database connection verified.")
    yield
    print("🛑 Application shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Lead Generation Agent",
    description=(
        "An AI-powered system that automatically identifies, qualifies, and "
        "reaches out to potential business leads based on job postings."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers (imported here; modules added in later phases) ────────────────────
# from api.endpoints.ingestion_routes import router as ingestion_router
# from api.endpoints.lead_routes import router as lead_router
# from api.endpoints.outreach_routes import router as outreach_router
# app.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])
# app.include_router(lead_router, prefix="/leads", tags=["Leads"])
# app.include_router(outreach_router, prefix="/outreach", tags=["Outreach"])


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Returns service liveness status."""
    return {"status": "ok", "service": "ai-lead-gen-agent"}


@app.get("/", tags=["System"])
def root():
    return {
        "message": "AI Lead Generation Agent is running.",
        "docs": "/docs",
        "product": settings.product_description[:80] + "...",
    }
