"""
tests/test_ai_engine.py — Unit tests for the AI engine layer.

Tests helpers and output parsing WITHOUT making real LLM API calls.
The processor functions (generate_keywords, qualify_lead, draft_email) are
tested with mocked LLM responses to keep tests fast and free.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.ai_engine.utils import parse_json_safely, truncate_for_context
from app.ai_engine.processor import (
    QualificationResult,
    EmailDraft,
    qualify_lead,
    draft_email,
    generate_keywords,
)
from app.services.scoring import is_lead_qualified


# ── parse_json_safely ─────────────────────────────────────────────────────────

class TestParseJsonSafely:
    def test_parses_clean_json_object(self):
        text = '{"is_qualified": true, "relevance_score": 85}'
        result = parse_json_safely(text)
        assert result == {"is_qualified": True, "relevance_score": 85}

    def test_parses_clean_json_array(self):
        text = '["cto", "vp engineering", "head of engineering"]'
        result = parse_json_safely(text)
        assert result == ["cto", "vp engineering", "head of engineering"]

    def test_strips_markdown_code_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = parse_json_safely(text)
        assert result == {"key": "value"}

    def test_strips_plain_code_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_json_safely(text)
        assert result == {"key": "value"}

    def test_extracts_json_from_surrounding_text(self):
        text = 'Here is the result:\n{"score": 75}\nDone.'
        result = parse_json_safely(text)
        assert result == {"score": 75}

    def test_returns_none_for_invalid_json(self):
        result = parse_json_safely("This is not JSON at all.")
        assert result is None

    def test_returns_none_for_empty_string(self):
        result = parse_json_safely("")
        assert result is None

    def test_returns_none_for_none(self):
        result = parse_json_safely(None)
        assert result is None


# ── truncate_for_context ──────────────────────────────────────────────────────

class TestTruncateForContext:
    def test_short_string_unchanged(self):
        text = "Short text"
        assert truncate_for_context(text, max_chars=100) == text

    def test_long_string_truncated(self):
        text = "a" * 3000
        result = truncate_for_context(text, max_chars=2000)
        assert len(result) == 2003  # 2000 chars + "..."
        assert result.endswith("...")

    def test_exact_length_unchanged(self):
        text = "a" * 2000
        assert truncate_for_context(text, max_chars=2000) == text

    def test_empty_string(self):
        assert truncate_for_context("", max_chars=100) == ""

    def test_none_returns_empty(self):
        assert truncate_for_context(None, max_chars=100) == ""


# ── qualify_lead (mocked LLM) ─────────────────────────────────────────────────

class TestQualifyLead:
    def _mock_llm_response(self, content: str):
        """Build a mock LangChain response object."""
        mock = MagicMock()
        mock.content = content
        return mock

    @patch("app.ai_engine.processor.build_openrouter_llm")
    def test_valid_qualification_response(self, mock_build_llm):
        """LLM returns well-formed JSON → QualificationResult populated correctly."""
        llm_response = json.dumps({
            "is_qualified": True,
            "relevance_score": 82,
            "reason": "Company is building a large engineering team and needs code review tooling.",
            "target_contact_role": "Head of Engineering",
            "company_pain_points": ["code quality", "slow reviews", "scaling eng team"],
        })
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = self._mock_llm_response(llm_response)
        mock_build_llm.return_value = MagicMock()

        # Patch the chain construction (prompt | llm)
        with patch("app.ai_engine.processor.LEAD_QUALIFICATION_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            result = qualify_lead(
                company_name="TechCorp",
                job_title="Senior Software Engineer",
                job_description="We build developer tools.",
                location="Remote",
                product_description="An AI code review tool.",
            )

        assert result.is_qualified is True
        assert result.relevance_score == 82.0
        assert result.target_contact_role == "Head of Engineering"
        assert len(result.company_pain_points) == 3

    @patch("app.ai_engine.processor.build_openrouter_llm")
    def test_malformed_response_returns_safe_default(self, mock_build_llm):
        """LLM returns garbage → safe default QualificationResult returned."""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = self._mock_llm_response("Sorry, I cannot help.")
        mock_build_llm.return_value = MagicMock()

        with patch("app.ai_engine.processor.LEAD_QUALIFICATION_PROMPT") as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            result = qualify_lead(
                company_name="BadCo",
                job_title="Designer",
                job_description="",
                location="NYC",
                product_description="A code review tool.",
            )

        assert result.is_qualified is False
        assert result.relevance_score == 0.0


# ── scoring ───────────────────────────────────────────────────────────────────

class TestScoring:
    def _make_result(self, is_qualified: bool, score: float) -> QualificationResult:
        return QualificationResult(
            is_qualified=is_qualified,
            relevance_score=score,
            reason="test",
            target_contact_role="CTO",
            company_pain_points=[],
            raw_response="{}",
        )

    def test_qualified_above_threshold(self):
        # Default MIN_RELEVANCE_SCORE is 60 in settings
        result = self._make_result(is_qualified=True, score=75.0)
        assert is_lead_qualified(result) is True

    def test_qualified_flag_false_fails(self):
        result = self._make_result(is_qualified=False, score=90.0)
        assert is_lead_qualified(result) is False

    def test_score_below_threshold_fails(self):
        result = self._make_result(is_qualified=True, score=30.0)
        assert is_lead_qualified(result) is False

    def test_exactly_at_threshold_passes(self):
        result = self._make_result(is_qualified=True, score=60.0)
        assert is_lead_qualified(result) is True
