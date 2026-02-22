"""
tests/test_outreach.py — Unit tests for the outreach module.

Tests template rendering and GmailMailer in dry-run mode.
No actual emails are sent and no SMTP connections are opened.

conftest.py sets dummy env vars so pydantic-settings doesn't block.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from io import StringIO

from app.outreach.templates import render_email, RenderedEmail
from app.outreach.mailer import GmailMailer
from app.db.models import DeliveryStatus


# ── render_email ──────────────────────────────────────────────────────────────

class TestRenderEmail:
    def test_returns_rendered_email_dataclass(self):
        result = render_email("Hello!", "Hi there.\nHow are you?")
        assert isinstance(result, RenderedEmail)

    def test_subject_preserved_exactly(self):
        result = render_email("Re: Your Engineering Hiring", "Body text.")
        assert result.subject == "Re: Your Engineering Hiring"

    def test_plain_body_preserved(self):
        body = "Hello,\n\nWe'd love to help.\n\nBest,\nVithu"
        result = render_email("Subject", body)
        assert result.plain_body == body

    def test_html_body_contains_subject(self):
        result = render_email("My Subject", "Some body text.")
        assert "My Subject" in result.html_body

    def test_html_body_contains_body_text(self):
        result = render_email("Subject", "Unique content XYZ123.")
        assert "Unique content XYZ123." in result.html_body

    def test_html_body_is_valid_html_structure(self):
        result = render_email("Subject", "Body.")
        assert "<!DOCTYPE html>" in result.html_body
        assert "<html" in result.html_body
        assert "</html>" in result.html_body
        assert "<body" in result.html_body
        assert "</body>" in result.html_body

    def test_html_body_wraps_paragraphs(self):
        result = render_email("Subject", "Line one.\nLine two.")
        assert "<p>" in result.html_body

    def test_custom_sender_name_in_html(self):
        result = render_email("Subject", "Body.", sender_name="Alice")
        assert "Alice" in result.html_body

    def test_default_sender_name_used(self):
        result = render_email("Subject", "Body.")
        # Default sender_name is "Vithusan"
        assert "Vithusan" in result.html_body

    def test_empty_body_does_not_crash(self):
        result = render_email("Subject", "")
        assert result.plain_body == ""
        assert "<!DOCTYPE html>" in result.html_body


# ── GmailMailer — dry-run ─────────────────────────────────────────────────────

class TestGmailMailerDryRun:
    """Test the mailer in dry-run mode — no SMTP connection is ever opened."""

    @pytest.fixture
    def mailer(self):
        """Always in dry-run regardless of .env."""
        return GmailMailer(dry_run=True)

    @pytest.fixture
    def mock_db(self):
        """Minimal mock for SQLAlchemy session."""
        db = MagicMock()
        return db

    @pytest.fixture
    def sample_email(self):
        return render_email(
            subject="Quick question about your engineering hiring",
            plain_body="Hi,\n\nI noticed you're hiring an Engineering Manager...\n\nBest,\nVithu",
        )

    def test_send_returns_true_in_dry_run(self, mailer, mock_db, sample_email):
        from app.db.repository import log_outreach_email, update_email_delivery_status
        with patch("app.outreach.mailer.repository") as mock_repo:
            mock_repo.log_outreach_email.return_value = MagicMock(id=1)
            result = mailer.send(
                db=mock_db,
                lead_id=1,
                to_address="cto@example.com",
                email=sample_email,
            )
        assert result is True

    def test_send_does_not_call_smtp(self, mailer, mock_db, sample_email):
        """Dry-run must never open an SMTP connection."""
        with patch("app.outreach.mailer.repository") as mock_repo:
            mock_repo.log_outreach_email.return_value = MagicMock(id=1)
            with patch("app.outreach.mailer.smtplib.SMTP_SSL") as mock_smtp:
                mailer.send(
                    db=mock_db, lead_id=1,
                    to_address="cto@example.com", email=sample_email,
                )
                mock_smtp.assert_not_called()

    def test_send_logs_email_to_db(self, mailer, mock_db, sample_email):
        """Dry-run should still log the email record to the DB."""
        with patch("app.outreach.mailer.repository") as mock_repo:
            mock_repo.log_outreach_email.return_value = MagicMock(id=42)
            mailer.send(
                db=mock_db, lead_id=7,
                to_address="hr@startup.io", email=sample_email,
            )
            mock_repo.log_outreach_email.assert_called_once()
            call_kwargs = mock_repo.log_outreach_email.call_args.kwargs
            assert call_kwargs["lead_id"] == 7
            assert call_kwargs["subject"] == sample_email.subject

    def test_send_updates_status_to_sent(self, mailer, mock_db, sample_email):
        """After dry-run, delivery status should be updated to SENT."""
        with patch("app.outreach.mailer.repository") as mock_repo:
            mock_repo.log_outreach_email.return_value = MagicMock(id=99)
            mailer.send(
                db=mock_db, lead_id=1,
                to_address="test@example.com", email=sample_email,
            )
            mock_repo.update_email_delivery_status.assert_called_once_with(
                mock_db, 99, DeliveryStatus.SENT
            )

    def test_dry_run_prints_to_stdout(self, mailer, mock_db, sample_email, capsys):
        """Dry-run should print the email body and subject to stdout."""
        with patch("app.outreach.mailer.repository") as mock_repo:
            mock_repo.log_outreach_email.return_value = MagicMock(id=1)
            mailer.send(
                db=mock_db, lead_id=1,
                to_address="cto@example.com", email=sample_email,
            )
        captured = capsys.readouterr()
        assert sample_email.subject in captured.out
        assert "DRY RUN" in captured.out


# ── GmailMailer init ──────────────────────────────────────────────────────────

class TestGmailMailerInit:
    def test_dry_run_kwarg_overrides_settings(self):
        mailer = GmailMailer(dry_run=True)
        assert mailer.dry_run is True

    def test_dry_run_false_kwarg(self):
        mailer = GmailMailer(dry_run=False)
        assert mailer.dry_run is False

    def test_uses_settings_when_no_kwarg(self):
        """Without a kwarg, dry_run should come from settings."""
        from app.config import settings
        mailer = GmailMailer()
        assert mailer.dry_run == settings.mailer_dry_run
