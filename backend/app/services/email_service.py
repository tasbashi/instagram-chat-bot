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


# ═══════════════════════════════════════════════════════════════════
# AGENT EVENT NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════


async def _resolve_owner_email(agent_id: str) -> tuple[str | None, bool]:
    """Resolve the owner email for an agent and check send_email permission.

    Returns (email, has_permission). email is None if agent/user not found.
    """
    from sqlalchemy import select
    from app.db.session import async_session_factory
    from app.models.agent import Agent
    from app.models.instagram_account import InstagramAccount
    from app.models.user import User

    async with async_session_factory() as db:
        import uuid as uuid_mod

        result = await db.execute(
            select(User.email, Agent.permissions)
            .join(InstagramAccount, InstagramAccount.user_id == User.id)
            .join(Agent, Agent.instagram_account_id == InstagramAccount.id)
            .where(Agent.id == uuid_mod.UUID(agent_id))
            .limit(1)
        )
        row = result.first()
        if not row:
            logger.warning("Cannot resolve owner for agent %s", agent_id)
            return None, False

        email, permissions = row
        has_perm = (permissions or {}).get("send_email", False)
        return email, has_perm


def _event_email_wrapper(
    title: str,
    subtitle: str,
    details: list[tuple[str, str]],
    accent: str = "#8b5cf6",
    emoji: str = "📅",
    footer: str | None = None,
) -> str:
    """Build a branded HTML email body for event notifications."""
    rows = "".join(
        f'<tr><td style="color:#9ca3af;font-size:13px;padding:6px 12px 6px 0;'
        f'white-space:nowrap;vertical-align:top;">{label}</td>'
        f'<td style="color:#e5e7eb;font-size:13px;padding:6px 0;'
        f'font-weight:500;">{value}</td></tr>'
        for label, value in details
    )
    footer_html = (
        f'<p style="color:#6b7280;font-size:12px;margin:16px 0 0;">{footer}</p>'
        if footer
        else ""
    )
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0d0d12;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d0d12;padding:40px 20px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#16161e;border-radius:12px;border:1px solid rgba(255,255,255,0.06);">
        <tr><td style="padding:36px 32px 24px;text-align:center;">
          <div style="display:inline-block;width:44px;height:44px;border-radius:11px;background:linear-gradient(135deg,{accent},#ec4899,#f97316);line-height:44px;font-size:20px;margin-bottom:20px;">{emoji}</div>
          <h1 style="color:#ffffff;font-size:20px;font-weight:700;margin:0 0 6px;letter-spacing:-0.3px;">{title}</h1>
          <p style="color:#9ca3af;font-size:14px;margin:0 0 24px;">{subtitle}</p>
          <div style="background:#1e1e2a;border:1px solid rgba(139,92,246,0.15);border-radius:10px;padding:16px 20px;text-align:left;">
            <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
          </div>
          {footer_html}
        </td></tr>
        <tr><td style="padding:0 32px 28px;">
          <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:16px;">
            <p style="color:#4b5563;font-size:11px;margin:0;text-align:center;">InstaBot — Automated notification</p>
          </div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def notify_appointment_created(agent_id: str, data: dict) -> None:
    """Send appointment confirmation email to agent owner (if permitted)."""
    email, has_perm = await _resolve_owner_email(agent_id)
    if not email or not has_perm:
        logger.info("Skipping appointment-created email (perm=%s, email=%s)", has_perm, bool(email))
        return

    subject = f"✅ New Appointment — {data.get('customer_name', '')} {data.get('customer_surname', '')}".strip()
    details = [
        ("Customer", f"{data.get('customer_name', '')} {data.get('customer_surname', '')}"),
        ("Date", data.get("date", "")),
        ("Time", data.get("time", "")),
        ("Subject", data.get("subject", "—")),
    ]
    if data.get("service_type"):
        details.append(("Service", data["service_type"]))

    plain = (
        f"New appointment booked:\n"
        f"Customer: {data.get('customer_name', '')} {data.get('customer_surname', '')}\n"
        f"Date: {data.get('date', '')}  Time: {data.get('time', '')}\n"
        f"Subject: {data.get('subject', '—')}\n"
    )
    html = _event_email_wrapper(
        title="New Appointment Confirmed",
        subtitle="A customer just booked an appointment via Instagram",
        details=details,
        accent="#22c55e",
        emoji="✅",
    )
    await send_email(email, subject, plain, html=html)


async def notify_appointment_cancelled(agent_id: str, data: dict) -> None:
    """Send appointment cancellation email to agent owner (if permitted)."""
    email, has_perm = await _resolve_owner_email(agent_id)
    if not email or not has_perm:
        return

    subject = f"❌ Appointment Cancelled — {data.get('customer_name', '')} {data.get('customer_surname', '')}".strip()
    details = [
        ("Customer", f"{data.get('customer_name', '')} {data.get('customer_surname', '')}"),
        ("Date", data.get("date", "")),
        ("Time", data.get("time", "")),
        ("Reason", data.get("reason", "—")),
    ]

    plain = (
        f"Appointment cancelled:\n"
        f"Customer: {data.get('customer_name', '')} {data.get('customer_surname', '')}\n"
        f"Date: {data.get('date', '')}  Time: {data.get('time', '')}\n"
        f"Reason: {data.get('reason', '—')}\n"
    )
    html = _event_email_wrapper(
        title="Appointment Cancelled",
        subtitle="A customer's appointment has been cancelled",
        details=details,
        accent="#ef4444",
        emoji="❌",
    )
    await send_email(email, subject, plain, html=html)


async def notify_appointment_rescheduled(agent_id: str, data: dict) -> None:
    """Send appointment reschedule email to agent owner (if permitted)."""
    email, has_perm = await _resolve_owner_email(agent_id)
    if not email or not has_perm:
        return

    subject = f"🔄 Appointment Updated — {data.get('customer_name', '')} {data.get('customer_surname', '')}".strip()
    details = [
        ("Customer", f"{data.get('customer_name', '')} {data.get('customer_surname', '')}"),
        ("New Date", data.get("date", "")),
        ("New Time", data.get("time", "")),
        ("Subject", data.get("subject", "—")),
    ]

    plain = (
        f"Appointment rescheduled:\n"
        f"Customer: {data.get('customer_name', '')} {data.get('customer_surname', '')}\n"
        f"New date: {data.get('date', '')}  New time: {data.get('time', '')}\n"
        f"Subject: {data.get('subject', '—')}\n"
    )
    html = _event_email_wrapper(
        title="Appointment Rescheduled",
        subtitle="An appointment has been updated with new details",
        details=details,
        accent="#f59e0b",
        emoji="🔄",
    )
    await send_email(email, subject, plain, html=html)


async def notify_compliment_received(agent_id: str, data: dict) -> None:
    """Send compliment notification email to agent owner (if permitted)."""
    email, has_perm = await _resolve_owner_email(agent_id)
    if not email or not has_perm:
        return

    subject = "⭐ New Compliment Received"
    details = [
        ("From", data.get("customer_ig_id", "Instagram user")),
        ("Message", data.get("content", "")),
    ]

    plain = (
        f"New compliment from {data.get('customer_ig_id', 'a customer')}:\n"
        f"\"{data.get('content', '')}\"\n"
    )
    html = _event_email_wrapper(
        title="New Compliment ⭐",
        subtitle="A customer shared some positive feedback",
        details=details,
        accent="#eab308",
        emoji="⭐",
        footer="Keep up the great work!",
    )
    await send_email(email, subject, plain, html=html)
