"""
app/outreach/mailer.py — Gmail SMTP mailer with dry-run support.

GmailMailer sends (or simulates sending) outreach emails and logs
every attempt to the database via the repository layer.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.db import repository
from app.db.models import DeliveryStatus
from app.outreach.templates import RenderedEmail

logger = logging.getLogger(__name__)

# Gmail SMTP constants
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 465  # SSL


class GmailMailer:
    """
    Sends outreach emails via Gmail SMTP using an App Password.

    In dry-run mode (MAILER_DRY_RUN=true) emails are printed to stdout
    and never actually transmitted — safe for development and demos.
    """

    def __init__(self, dry_run: Optional[bool] = None):
        self.smtp_user = settings.gmail_user
        self.smtp_password = settings.gmail_app_password
        self.dry_run = dry_run if dry_run is not None else settings.mailer_dry_run

    # ── Public API ────────────────────────────────────────────────────────────

    def send(
        self,
        db: Session,
        lead_id: int,
        to_address: str,
        email: RenderedEmail,
    ) -> bool:
        """
        Send (or simulate) a single outreach email and log it to the DB.

        Args:
            db:         Active SQLAlchemy session.
            lead_id:    ID of the Lead this email belongs to.
            to_address: Recipient email address.
            email:      Rendered email (subject + html + plain bodies).

        Returns:
            True on success (real send or dry-run), False on send failure.
        """
        # Log the attempt before sending (pending status)
        email_record = repository.log_outreach_email(
            db=db,
            lead_id=lead_id,
            subject=email.subject,
            body=email.plain_body,
            to_address=to_address,
            delivery_status=DeliveryStatus.PENDING,
        )

        if self.dry_run:
            self._print_dry_run(to_address, email)
            repository.update_email_delivery_status(
                db, email_record.id, DeliveryStatus.SENT
            )
            db.commit()
            logger.info("DRY RUN: email to %s logged (not sent).", to_address)
            return True

        try:
            self._send_via_smtp(to_address, email)
            repository.update_email_delivery_status(
                db, email_record.id, DeliveryStatus.SENT
            )
            db.commit()
            logger.info("Email sent to %s (lead_id=%d).", to_address, lead_id)
            return True
        except Exception as exc:
            error_msg = str(exc)
            repository.update_email_delivery_status(
                db, email_record.id, DeliveryStatus.FAILED, error_message=error_msg
            )
            db.commit()
            logger.error("Failed to send email to %s: %s", to_address, error_msg)
            return False

    # ── Private helpers ───────────────────────────────────────────────────────

    def _send_via_smtp(self, to_address: str, email: RenderedEmail) -> None:
        """Establish an SSL connection to Gmail and transmit the message."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = email.subject
        msg["From"] = self.smtp_user
        msg["To"] = to_address

        # Attach plain text first, HTML second — clients prefer the last part
        msg.attach(MIMEText(email.plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(email.html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, to_address, msg.as_string())

    @staticmethod
    def _print_dry_run(to_address: str, email: RenderedEmail) -> None:
        """Pretty-print the email to stdout for dry-run inspection."""
        separator = "─" * 60
        print(f"\n{separator}")
        print(f"  📧  DRY RUN — Email not sent")
        print(separator)
        print(f"  To      : {to_address}")
        print(f"  Subject : {email.subject}")
        print(separator)
        print(email.plain_body)
        print(f"{separator}\n")
