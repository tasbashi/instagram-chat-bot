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
    html: str | None = None,
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

    if html:
        msg.add_alternative(html, subtype="html")

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


async def send_verification_email(to: str, code: str) -> bool:
    """Send a branded 6-digit verification code email."""
    subject = f"{code} is your InstaBot verification code"

    plain = (
        f"Your InstaBot verification code is: {code}\n\n"
        f"This code expires in {settings.verification_code_expiry_minutes} minutes.\n\n"
        "If you did not request this, please ignore this email."
    )

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0d0d12;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d12;padding:40px 20px;">
    <tr><td align="center">
      <table width="440" cellpadding="0" cellspacing="0" style="background:#16161e;border-radius:12px;border:1px solid rgba(255,255,255,0.06);">
        <tr><td style="padding:36px 32px 24px;text-align:center;">
          <div style="display:inline-block;width:44px;height:44px;border-radius:11px;background:linear-gradient(135deg,#8b5cf6,#ec4899,#f97316);line-height:44px;font-size:20px;margin-bottom:20px;">🤖</div>
          <h1 style="color:#ffffff;font-size:20px;font-weight:700;margin:0 0 6px;letter-spacing:-0.3px;">Verify your email</h1>
          <p style="color:#9ca3af;font-size:14px;margin:0 0 28px;">Enter this code to complete your registration</p>
          <div style="background:#1e1e2a;border:1px solid rgba(139,92,246,0.2);border-radius:10px;padding:20px;margin-bottom:24px;">
            <span style="font-size:32px;font-weight:700;letter-spacing:10px;color:#8b5cf6;font-family:'Courier New',monospace;">{code}</span>
          </div>
          <p style="color:#6b7280;font-size:12px;margin:0;">This code expires in {settings.verification_code_expiry_minutes} minutes</p>
        </td></tr>
        <tr><td style="padding:0 32px 28px;">
          <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:16px;">
            <p style="color:#4b5563;font-size:11px;margin:0;text-align:center;">If you didn't request this code, you can safely ignore this email.</p>
          </div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return await send_email(to, subject, plain, html=html)
