"""
tests/test_ingestion.py — Unit tests for the ingestion layer.

Runs without network calls or DB connections by using sample data.
"""

import pytest
from datetime import datetime

from app.ingestion.normalizer import normalize_job, normalize_jobs, _strip_html, _extract_domain
from app.ingestion.filters import keyword_filter, DEFAULT_BUYER_ROLES


# ── Sample data ───────────────────────────────────────────────────────────────

SAMPLE_RAW_JOB = {
    "id": "12345",
    "position": "senior software engineer",
    "company": "Acme Corp",
    "company_logo": "https://www.acmecorp.io/logo.png",
    "apply_url": "https://remoteok.com/jobs/12345",
    "location": "Remote",
    "description": "<p>We are looking for a <strong>Senior Engineer</strong> to join our team.</p>",
    "tags": ["python", "engineer", "remote"],
    "date": 1700000000,
}

SAMPLE_RAW_JOB_MISSING_FIELDS = {
    "id": "99999",
    # no 'position' or 'company' — should be skipped
    "description": "some description",
}

SAMPLE_RAW_JOB_NO_DESCRIPTION = {
    "id": "55555",
    "position": "CTO",
    "company": "StartupXYZ",
    "tags": ["leadership", "cto"],
    "date": 1700000000,
}


# ── normalizer tests ──────────────────────────────────────────────────────────

class TestNormalizerHelpers:
    def test_strip_html_removes_tags(self):
        raw = "<p>Hello <strong>World</strong></p>"
        assert _strip_html(raw) == "Hello World"

    def test_strip_html_empty_string(self):
        assert _strip_html("") == ""

    def test_strip_html_plain_text_unchanged(self):
        assert _strip_html("Just plain text") == "Just plain text"

    def test_extract_domain_basic(self):
        assert _extract_domain("https://www.acmecorp.io/logo.png") == "acmecorp.io"

    def test_extract_domain_strips_www(self):
        assert _extract_domain("https://www.example.com") == "example.com"

    def test_extract_domain_none(self):
        assert _extract_domain(None) is None

    def test_extract_domain_invalid(self):
        result = _extract_domain("not-a-url")
        # Should not raise; returns None or empty
        assert result is None or isinstance(result, str)


class TestNormalizeJob:
    def test_valid_job_normalizes_correctly(self):
        job = normalize_job(SAMPLE_RAW_JOB)
        assert job is not None
        assert job.title == "Senior Software Engineer"
        assert job.company_name == "Acme Corp"
        assert job.company_domain == "acmecorp.io"
        assert job.source == "remoteok"
        assert job.external_id == "12345"
        assert "Senior Engineer" in job.description
        assert "<p>" not in job.description   # HTML stripped
        assert job.location == "Remote"
        assert "python" in job.tags
        assert isinstance(job.posted_at, datetime)

    def test_missing_title_returns_none(self):
        result = normalize_job(SAMPLE_RAW_JOB_MISSING_FIELDS)
        assert result is None

    def test_job_without_description_uses_fallback(self):
        job = normalize_job(SAMPLE_RAW_JOB_NO_DESCRIPTION)
        assert job is not None
        assert job.title == "Cto"
        assert "CTO" in job.description or "leadership" in job.description.lower()

    def test_description_capped_at_4000_chars(self):
        raw = dict(SAMPLE_RAW_JOB)
        raw["description"] = "x" * 10000
        job = normalize_job(raw)
        assert job is not None
        assert len(job.description) <= 4000


class TestNormalizeJobs:
    def test_batch_normalizes_and_skips_invalid(self):
        raw_list = [SAMPLE_RAW_JOB, SAMPLE_RAW_JOB_MISSING_FIELDS, SAMPLE_RAW_JOB_NO_DESCRIPTION]
        results = normalize_jobs(raw_list)
        # 2 valid, 1 skipped
        assert len(results) == 2

    def test_empty_list_returns_empty(self):
        assert normalize_jobs([]) == []


# ── filter tests ──────────────────────────────────────────────────────────────

class TestKeywordFilter:
    def _make_job(self, title: str, tags: list[str] | None = None):
        """Helper: create a minimal NormalizedJob for testing."""
        from app.ingestion.normalizer import NormalizedJob
        return NormalizedJob(
            source="remoteok",
            external_id="1",
            title=title,
            company_name="TestCo",
            description="A job at TestCo.",
            tags=tags or [],
        )

    def test_cto_passes_filter(self):
        jobs = [self._make_job("CTO")]
        result = keyword_filter(jobs, keywords=DEFAULT_BUYER_ROLES)
        assert len(result) == 1

    def test_unrelated_role_filtered_out(self):
        jobs = [self._make_job("Graphic Designer")]
        result = keyword_filter(jobs, keywords=DEFAULT_BUYER_ROLES)
        assert len(result) == 0

    def test_tag_match_passes(self):
        jobs = [self._make_job("Some Role", tags=["devops"])]
        result = keyword_filter(jobs, keywords=["devops"])
        assert len(result) == 1

    def test_empty_jobs_returns_empty(self):
        assert keyword_filter([], keywords=DEFAULT_BUYER_ROLES) == []

    def test_custom_keywords(self):
        jobs = [self._make_job("Head of Marketing")]
        result = keyword_filter(jobs, keywords=["marketing"])
        assert len(result) == 1
