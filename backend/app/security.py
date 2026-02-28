"""Webhook signature verification middleware."""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import HTTPException, Request, status

from app.config import settings

logger = logging.getLogger("security")


async def verify_signature(request: Request) -> bytes:
    """Verify the X-Hub-Signature-256 header from Meta.

    Instagram webhooks are signed with the Instagram App Secret,
    not the Facebook App Secret. We try both for resilience.

    Returns the raw body bytes if valid, raises 403 if not.
    """
    body = await request.body()

    # Collect possible secrets (Instagram App Secret takes priority)
    secrets = []
    if settings.instagram_app_secret:
        secrets.append(settings.instagram_app_secret)
    if settings.app_secret:
        secrets.append(settings.app_secret)

    if not secrets:
        logger.debug("No app secrets set — skipping signature verification")
        return body

    signature_header = request.headers.get("X-Hub-Signature-256", "")

    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing signature header",
        )

    for secret in secrets:
        expected = "sha256=" + hmac.new(
            secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if hmac.compare_digest(signature_header, expected):
            return body

    logger.warning("Invalid webhook signature")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid signature",
    )
