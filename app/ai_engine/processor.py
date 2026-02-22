"""
app/ai_engine/processor.py — LangChain chain implementations for the AI engine.

Three public functions:
  generate_keywords(product_description)  → list[str]
  qualify_lead(job_posting, product)      → QualificationResult
  draft_email(lead_data, product)         → EmailDraft
"""

import json
import logging
from dataclasses import dataclass

from app.ai_engine.prompt_templates import (
    EMAIL_DRAFT_PROMPT,
    KEYWORD_GENERATION_PROMPT,
    LEAD_QUALIFICATION_PROMPT,
)
from app.ai_engine.utils import build_openrouter_llm, parse_json_safely, truncate_for_context

logger = logging.getLogger(__name__)


# ── Output dataclasses ────────────────────────────────────────────────────────

@dataclass
class QualificationResult:
    is_qualified: bool
    relevance_score: float          # 0.0 – 100.0
    reason: str
    target_contact_role: str
    company_pain_points: list[str]
    raw_response: str               # original LLM text (for debugging)


@dataclass
class EmailDraft:
    subject: str
    body: str
    raw_response: str               # original LLM text (for debugging)


# ── 1. Keyword Generation ─────────────────────────────────────────────────────

def generate_keywords(product_description: str) -> list[str]:
    """
    Generate B2B buyer-signal role keywords for the given product.

    Args:
        product_description: Free-text description of the product/service.

    Returns:
        List of lowercase role keyword strings.

    Raises:
        ValueError: If the LLM returns an unparseable response.
    """
    llm = build_openrouter_llm(temperature=0.2)
    chain = KEYWORD_GENERATION_PROMPT | llm

    logger.info("Generating role keywords for product: %s...", product_description[:60])

    response = chain.invoke({"product_description": product_description})
    raw_text = response.content if hasattr(response, "content") else str(response)

    parsed = parse_json_safely(raw_text)

    if not isinstance(parsed, list):
        logger.error("Keyword generation returned non-list: %s", raw_text[:200])
        raise ValueError(f"Expected a JSON array of strings, got: {type(parsed)}")

    keywords = [str(k).lower().strip() for k in parsed if k]
    logger.info("Generated %d keywords: %s", len(keywords), keywords[:5])
    return keywords


# ── 2. Lead Qualification ─────────────────────────────────────────────────────

def qualify_lead(
    company_name: str,
    job_title: str,
    job_description: str,
    location: str,
    product_description: str,
) -> QualificationResult:
    """
    Use the LLM to determine if a job posting signals a potential customer.

    Args:
        company_name:        Name of the hiring company.
        job_title:           The job title from the posting.
        job_description:     Full or truncated job description (plain text).
        location:            Job location string.
        product_description: Our product description.

    Returns:
        QualificationResult with score, reason, contact role, and pain points.
    """
    llm = build_openrouter_llm(temperature=0.1)  # low temp for consistent scoring
    chain = LEAD_QUALIFICATION_PROMPT | llm

    logger.info("Qualifying lead: %s @ %s", job_title, company_name)

    response = chain.invoke({
        "product_description": product_description,
        "company_name": company_name,
        "job_title": job_title,
        "location": location or "Remote",
        "job_description": truncate_for_context(job_description, max_chars=2000),
    })
    raw_text = response.content if hasattr(response, "content") else str(response)

    parsed = parse_json_safely(raw_text)

    if not isinstance(parsed, dict):
        logger.error("Qualification returned non-dict for %s: %s", company_name, raw_text[:200])
        # Return a safe default — mark as not qualified
        return QualificationResult(
            is_qualified=False,
            relevance_score=0.0,
            reason="LLM returned unparseable response.",
            target_contact_role="Unknown",
            company_pain_points=[],
            raw_response=raw_text,
        )

    pain_points = parsed.get("company_pain_points", [])
    if not isinstance(pain_points, list):
        pain_points = []

    result = QualificationResult(
        is_qualified=bool(parsed.get("is_qualified", False)),
        relevance_score=float(parsed.get("relevance_score", 0)),
        reason=str(parsed.get("reason", "")),
        target_contact_role=str(parsed.get("target_contact_role", "Unknown")),
        company_pain_points=pain_points,
        raw_response=raw_text,
    )

    logger.info(
        "Qualification result: is_qualified=%s score=%.1f for %s @ %s",
        result.is_qualified, result.relevance_score, job_title, company_name,
    )
    return result


# ── 3. Email Draft ────────────────────────────────────────────────────────────

def draft_email(
    company_name: str,
    job_title: str,
    contact_role: str,
    reason: str,
    pain_points: list[str],
    product_description: str,
) -> EmailDraft:
    """
    Generate a personalized cold outreach email for a qualified lead.

    Args:
        company_name:        Target company name.
        job_title:           The job posting title that triggered qualification.
        contact_role:        The ideal person to reach out to (from qualification).
        reason:              Why this company is a good fit (from qualification).
        pain_points:         List of company pain points (from qualification).
        product_description: Our product description.

    Returns:
        EmailDraft with subject and body.
    """
    llm = build_openrouter_llm(temperature=0.7)  # higher temp for natural-sounding copy
    chain = EMAIL_DRAFT_PROMPT | llm

    logger.info("Drafting email for: %s (contact: %s)", company_name, contact_role)

    pain_points_str = "\n".join(f"- {p}" for p in pain_points) if pain_points else "Not specified"

    response = chain.invoke({
        "product_description": product_description,
        "company_name": company_name,
        "job_title": job_title,
        "contact_role": contact_role,
        "reason": reason,
        "pain_points": pain_points_str,
    })
    raw_text = response.content if hasattr(response, "content") else str(response)

    parsed = parse_json_safely(raw_text)

    if not isinstance(parsed, dict) or "subject" not in parsed or "body" not in parsed:
        logger.error("Email draft returned invalid structure for %s: %s", company_name, raw_text[:200])
        # Safe fallback draft
        return EmailDraft(
            subject=f"Quick question about your {job_title} role",
            body=(
                f"Hi,\n\nI came across {company_name}'s recent {job_title} posting "
                f"and thought our product might be relevant to what your team is building.\n\n"
                f"Would you be open to a quick 15-minute chat?\n\nBest"
            ),
            raw_response=raw_text,
        )

    return EmailDraft(
        subject=str(parsed["subject"]),
        body=str(parsed["body"]),
        raw_response=raw_text,
    )
