"""Email service — send transactional emails via SMTP."""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger("email_service")


async def send_email(
    to: str,
    subject: str,
    body: str,
) -> bool:
    """Send an email via SMTP.

    Returns True if sent successfully, False otherwise.
    """
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP not configured — skipping email to %s", to)
        return False

    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=False,
            start_tls=True,
        )
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False
