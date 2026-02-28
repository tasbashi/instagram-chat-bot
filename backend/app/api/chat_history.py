"""Chat history routes — list conversations, view messages, update status."""

from __future__ import annotations

import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, DBSession
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.instagram_account import InstagramAccount
from app.models.message import Message
from app.schemas import (
    ConversationDetailOut,
    ConversationOut,
    ConversationStatusUpdate,
    MessageOut,
)

router = APIRouter(prefix="/api/conversations", tags=["chat_history"])


@router.get("")
async def list_conversations(
    db: DBSession,
    current_user: CurrentUser,
    agent_id: Annotated[uuid_mod.UUID | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConversationOut]:
    user_agent_ids = (
        select(Agent.id)
        .join(InstagramAccount)
        .where(InstagramAccount.user_id == current_user.id)
    )

    query = select(Conversation).where(Conversation.agent_id.in_(user_agent_ids))

    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)
    if status_filter:
        query = query.where(Conversation.status == status_filter)

    query = query.order_by(Conversation.last_message_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    conversations = result.scalars().all()
    return [ConversationOut.from_conversation(c) for c in conversations]


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> ConversationDetailOut:
    conversation = await _get_user_conversation(conversation_id, db, current_user)

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return ConversationDetailOut(
        conversation=ConversationOut.from_conversation(conversation),
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.put("/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: uuid_mod.UUID,
    body: ConversationStatusUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> ConversationOut:
    conversation = await _get_user_conversation(conversation_id, db, current_user)
    conversation.status = body.status

    if body.status == "resolved":
        conversation.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    return ConversationOut.from_conversation(conversation)


# ── Helpers ──────────────────────────────────────────────────────────


async def _get_user_conversation(
    conversation_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> Conversation:
    user_agent_ids = (
        select(Agent.id)
        .join(InstagramAccount)
        .where(InstagramAccount.user_id == current_user.id)
    )
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.agent_id.in_(user_agent_ids),
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return conversation
