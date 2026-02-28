"""Instagram Graph API client — send messages, get user info.

All requests go to graph.instagram.com (Business Login with IGA tokens).
Ref: https://developers.facebook.com/docs/instagram-platform/reference
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("instagram_api")

IG_GRAPH_URL = "https://graph.instagram.com/v25.0"
FB_GRAPH_URL = "https://graph.facebook.com/v25.0"


async def send_text_message(
    recipient_id: str,
    text: str,
    access_token: str,
) -> bool:
    """Send a text DM to an Instagram user.

    POST /me/messages
    Body: {"recipient": {"id": recipient_id}, "message": {"text": text}}

    The /me endpoint resolves to the professional account identified by
    the access_token. This is the correct approach for Business Login
    since the token already encodes which account is sending.
    """
    if not access_token:
        logger.warning("No access token — skipping message send")
        return False

    url = f"{IG_GRAPH_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            json=payload,
            params={"access_token": access_token},
        )

    if resp.status_code != 200:
        logger.error("Send failed (%s): %s", resp.status_code, resp.text)
        return False

    logger.info("✅ Reply sent to %s", recipient_id)
    return True


async def get_user_profile(
    user_id: str, access_token: str
) -> dict[str, Any] | None:
    """Fetch basic profile info for an Instagram user.

    GET /{user_id}?fields=username,name
    """
    url = f"{IG_GRAPH_URL}/{user_id}"
    params = {
        "fields": "username,name,profile_pic",
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        logger.warning("Profile fetch failed for %s: %s", user_id, resp.text)
        return None

    return resp.json()
