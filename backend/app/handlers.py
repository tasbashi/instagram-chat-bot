"""Instagram webhook event handlers."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_orchestrator import handle_incoming_message

logger = logging.getLogger("instagram_webhook")


async def handle_message(
    sender_id: str,
    message: dict[str, Any],
    db: AsyncSession,
    recipient_ig_id: str = "",
) -> None:
    """Process an incoming direct message — route to agent orchestrator."""
    text = message.get("text")
    ig_message_id = message.get("mid")
    attachments = message.get("attachments")

    logger.info("📩 Message from %s → %s — text=%s", sender_id, recipient_ig_id, text)

    if text:
        await handle_incoming_message(
            sender_ig_id=sender_id,
            recipient_ig_id=recipient_ig_id,
            message_text=text,
            ig_message_id=ig_message_id,
            db=db,
        )
    elif attachments:
        # For now, acknowledge attachments but don't process them
        await handle_incoming_message(
            sender_ig_id=sender_id,
            recipient_ig_id=recipient_ig_id,
            message_text="[Customer sent an attachment]",
            ig_message_id=ig_message_id,
            db=db,
        )


async def handle_postback(
    sender_id: str,
    postback: dict[str, Any],
    db: AsyncSession,
    recipient_ig_id: str = "",
) -> None:
    """Handle quick-reply / postback payloads."""
    payload = postback.get("payload", "")
    logger.info("🔘 Postback from %s → %s — payload=%s", sender_id, recipient_ig_id, payload)

    if payload:
        await handle_incoming_message(
            sender_ig_id=sender_id,
            recipient_ig_id=recipient_ig_id,
            message_text=f"[Postback: {payload}]",
            ig_message_id=None,
            db=db,
        )


async def handle_story_mention(
    sender_id: str, story: dict[str, Any], db: AsyncSession
) -> None:
    """Handle story mention events."""
    logger.info("📖 Story mention from %s — %s", sender_id, story)
