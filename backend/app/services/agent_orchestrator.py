"""Agent orchestrator — the brain that connects messages → LLM → tools → replies."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.instagram_account import InstagramAccount
from app.models.message import Message
from app.services.llm_client import chat_completion, extract_response, parse_tool_call_args
from app.services.instagram_api import send_text_message, get_user_profile
from app.tools.executors import create_tool_registry

logger = logging.getLogger("agent_orchestrator")

# Singleton registry
_tool_registry = create_tool_registry()

DEFAULT_SYSTEM_PROMPT = """You are a friendly, professional business assistant responding to customer inquiries via Instagram Direct Messages.

STRICT RULES — NEVER BREAK THESE:
1. NEVER mention tool names, function names, or internal systems to the customer. The customer must never see words like "search_knowledge", "send_email", "manage_appointment", "collect_compliment", or any function/tool reference.
2. NEVER claim you have performed an action (sent an email, booked an appointment) unless you actually called the tool AND received a success confirmation. If a tool call fails, tell the customer honestly.
3. NEVER fabricate or guess information. If the knowledge search returns no results, say "I don't have that information right now" instead of making something up.
4. Always respond in the SAME LANGUAGE the customer is using.

APPOINTMENT BOOKING — MANDATORY WORKFLOW:
When a customer wants to book an appointment, you MUST follow these steps IN ORDER:
1. COLLECT the following from the customer (do NOT skip any):
   - Full name (first name AND surname)
   - Desired date
   - Subject / reason for the appointment
2. ONCE you have the desired date, CHECK AVAILABILITY first using the check_availability action.
3. PRESENT the available time slots to the customer and ASK them to choose one. NEVER auto-pick a slot.
4. WAIT for the customer to confirm their preferred time slot.
5. BEFORE creating the appointment, SUMMARIZE all details to the customer and ask "Shall I confirm this appointment?" or similar.
6. ONLY after the customer explicitly confirms, CREATE the appointment.
If a time conflict occurs, show the alternative times and let the customer choose.

BEHAVIOR:
- When a customer asks a question, search your knowledge base FIRST, then answer based on the results.
- Give direct, helpful answers. Do not deflect with "Would you like me to send you an email?" when you can answer directly.
- Keep responses concise — this is Instagram DM, not an email. Use short paragraphs and bullet points.
- Be warm and approachable, not robotic.
- If you genuinely don't know something, say so and suggest the customer contact the business directly.
"""

MAX_CONVERSATION_CONTEXT = 10  # Last N messages to include in LLM context
MAX_TOOL_ROUNDS = 5  # Prevent infinite tool-calling loops


async def handle_incoming_message(
    sender_ig_id: str,
    message_text: str,
    ig_message_id: str | None,
    db: AsyncSession,
    recipient_ig_id: str = "",
) -> None:
    """Core orchestration: receive DM → find agent → LLM → tools → reply.

    This is the main entry point called by the webhook handler.
    recipient_ig_id is the IGSID from the webhook entry["id"].
    """
    # ── Step 1: Find the agent for this IG account ──
    agent, ig_account = await _resolve_agent(db, recipient_ig_id, sender_ig_id)

    if not agent or not ig_account:
        logger.info("⏭️ No active agent for recipient %s — skipping", recipient_ig_id)
        return

    # ── Guard: validate before doing any LLM work ──
    access_token = ig_account.page_access_token
    permissions = agent.permissions or {}

    if not access_token:
        logger.warning("⏭️ No access token for @%s — skipping", ig_account.ig_username)
        return

    if not permissions.get("read_messages", True):
        logger.info("⏭️ read_messages disabled for agent %s — skipping", agent.name)
        return

    if not permissions.get("write_messages", True):
        logger.info("⏭️ write_messages disabled for agent %s — skipping LLM", agent.name)
        return

    # ── Step 2: Get or create conversation ──
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.agent_id == agent.id,
            Conversation.customer_ig_id == sender_ig_id,
            Conversation.status == "active",
        )
    )
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        conversation = Conversation(
            agent_id=agent.id,
            customer_ig_id=sender_ig_id,
            status="active",
        )
        db.add(conversation)
        await db.flush()

    # Fetch username + profile pic if not yet stored
    if not conversation.customer_username:
        try:
            profile = await get_user_profile(sender_ig_id, access_token)
            if profile:
                if profile.get("username"):
                    conversation.customer_username = profile["username"]
                if profile.get("profile_picture_url"):
                    conversation.customer_profile_pic = profile["profile_picture_url"]
                logger.info("Resolved profile: %s → @%s", sender_ig_id, profile.get("username"))
        except Exception:
            logger.debug("Could not fetch profile for %s", sender_ig_id)

    # ── Step 3: Save incoming message ──
    customer_message = Message(
        conversation_id=conversation.id,
        sender_type="customer",
        content=message_text,
        ig_message_id=ig_message_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(customer_message)
    conversation.message_count += 1
    conversation.last_message_at = datetime.now(timezone.utc)
    await db.flush()

    # ── Step 4: Build LLM context ──
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(MAX_CONVERSATION_CONTEXT)
    )
    history_messages = list(reversed(msg_result.scalars().all()))

    system_prompt = (agent.system_context or "") + "\n\n" + DEFAULT_SYSTEM_PROMPT

    llm_messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt}
    ]

    for msg in history_messages:
        if msg.sender_type == "customer":
            llm_messages.append({"role": "user", "content": msg.content})
        elif msg.sender_type == "agent":
            llm_messages.append({"role": "assistant", "content": msg.content})

    # ── Step 5: Call LLM with tool loop ──
    tool_schemas = _tool_registry.get_schemas(permissions)

    tool_context = {
        "agent_id": str(agent.id),
        "customer_ig_id": sender_ig_id,
        "conversation_id": str(conversation.id),
    }

    all_tool_calls_log: list[dict] = []
    all_rag_context: list[dict] = []
    final_text = ""

    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            response_data = await chat_completion(
                messages=llm_messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=agent.llm_config.get("temperature", 0.3),
                max_tokens=agent.llm_config.get("max_tokens", 2048),
                llm_config=agent.llm_config,
            )
        except RuntimeError as exc:
            # Malformed tool call (Groq 400) — retry without tools
            logger.warning("LLM tool call failed: %s — retrying without tools", exc)
            try:
                response_data = await chat_completion(
                    messages=llm_messages,
                    tools=None,
                    temperature=agent.llm_config.get("temperature", 0.3),
                    max_tokens=agent.llm_config.get("max_tokens", 2048),
                    llm_config=agent.llm_config,
                )
            except Exception:
                logger.exception("LLM retry also failed")
                final_text = "I'm sorry, I'm having trouble processing your request right now. Please try again."
                break

        parsed = extract_response(response_data)

        # If no tool calls, we have the final response
        if not parsed["tool_calls"]:
            final_text = parsed["content"] or ""
            break

        # Process tool calls
        # Add assistant message with tool calls to context
        llm_messages.append({
            "role": "assistant",
            "content": parsed["content"],
            "tool_calls": parsed["tool_calls"],
        })

        for tool_call in parsed["tool_calls"]:
            func_name = tool_call["function"]["name"]
            args = parse_tool_call_args(tool_call)
            tool_call_id = tool_call["id"]

            logger.info("Tool call: %s(%s)", func_name, json.dumps(args, ensure_ascii=False)[:200])

            tool = _tool_registry.get(func_name)
            if tool:
                result_str = await tool.execute(args, tool_context)
            else:
                result_str = json.dumps({"error": f"Unknown tool: {func_name}"}, ensure_ascii=False)

            # Log tool call
            all_tool_calls_log.append({
                "tool": func_name,
                "args": args,
                "result": result_str[:500],
            })

            # If it was a knowledge search, log the RAG context
            if func_name == "search_knowledge":
                try:
                    rag_data = json.loads(result_str)
                    if "results" in rag_data:
                        all_rag_context.extend(rag_data["results"])
                except json.JSONDecodeError:
                    pass

            # Add tool result to LLM context
            llm_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_str,
            })

    if not final_text:
        final_text = "I'm sorry, I couldn't process your request. Please try again."

    # ── Step 5b: Derive tags from tool calls ──
    if all_tool_calls_log:
        new_tags = _derive_tags(all_tool_calls_log)
        if new_tags:
            meta = dict(conversation.metadata_) if conversation.metadata_ else {}
            existing_tags = list(meta.get("tags", []))
            for t in new_tags:
                if t not in existing_tags:
                    existing_tags.append(t)
            meta["tags"] = existing_tags
            conversation.metadata_ = meta

    # ── Step 6: Save agent response ──
    agent_message = Message(
        conversation_id=conversation.id,
        sender_type="agent",
        content=final_text,
        tool_calls=all_tool_calls_log if all_tool_calls_log else None,
        rag_context=all_rag_context if all_rag_context else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(agent_message)
    conversation.message_count += 1
    conversation.last_message_at = datetime.now(timezone.utc)
    await db.flush()

    # ── Step 7: Send reply via Instagram (chunked if >1000 chars) ──
    chunks = _split_message(final_text, max_len=1000)
    for i, chunk in enumerate(chunks):
        if i > 0:
            await asyncio.sleep(0.3)  # small delay so chunks arrive in order
        await send_text_message(sender_ig_id, chunk, access_token)

    logger.info(
        "Orchestration complete: %d tool calls, %d chars response",
        len(all_tool_calls_log), len(final_text),
    )


# ── Tag derivation ──────────────────────────────────────────────────


def _derive_tags(tool_calls_log: list[dict]) -> set[str]:
    """Inspect executed tool calls and return semantic tags for the conversation."""
    tags: set[str] = set()

    for entry in tool_calls_log:
        tool = entry.get("tool", "")
        result_str = entry.get("result", "")

        try:
            result = json.loads(result_str) if isinstance(result_str, str) else result_str
        except (json.JSONDecodeError, TypeError):
            result = {}

        if tool == "manage_appointment":
            status = result.get("status", "")
            if status == "confirmed":
                tags.add("appointment_created")
            elif status == "cancelled":
                tags.add("appointment_cancelled")
            if "available_slots" in result:
                tags.add("availability_checked")

        elif tool == "collect_compliment":
            if result.get("status") == "recorded":
                tags.add("compliment")

        elif tool == "send_email":
            if result.get("status") == "sent":
                tags.add("email_sent")

        elif tool == "search_knowledge":
            if result.get("result_count", 0) > 0:
                tags.add("knowledge_used")

    return tags


# ── Message chunking ────────────────────────────────────────────────


def _split_message(text: str, max_len: int = 1000) -> list[str]:
    """Split a long message into chunks at natural boundaries.

    Priority order:
    1. Paragraph boundaries (double newline)
    2. Line boundaries (single newline)
    3. Sentence endings (. ! ?)
    4. Word boundaries (space)

    Returns a list of chunks, each <= max_len characters.
    """
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []

    # Step 1: Split into paragraphs first
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para

        if len(candidate) <= max_len:
            current = candidate
        else:
            # Flush what we have
            if current:
                chunks.append(current.strip())
                current = ""

            # If this single paragraph fits, start a new chunk
            if len(para) <= max_len:
                current = para
            else:
                # Paragraph too long — split at finer boundaries
                chunks.extend(_split_block(para, max_len))

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]


def _split_block(text: str, max_len: int) -> list[str]:
    """Split a single block (no double-newlines) at line or sentence boundaries."""
    # Try line boundaries first
    lines = text.split("\n")
    if len(lines) > 1:
        chunks: list[str] = []
        current = ""
        for line in lines:
            candidate = f"{current}\n{line}" if current else line
            if len(candidate) <= max_len:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                if len(line) <= max_len:
                    current = line
                else:
                    chunks.extend(_split_sentences(line, max_len))
                    current = ""
        if current.strip():
            chunks.append(current.strip())
        return chunks

    # No line breaks — fall through to sentence splitting
    return _split_sentences(text, max_len)


def _split_sentences(text: str, max_len: int) -> list[str]:
    """Split text at sentence boundaries (. ! ?)."""
    import re
    # Split after sentence-ending punctuation followed by a space
    parts = re.split(r'(?<=[.!?])\s+', text)

    if len(parts) <= 1:
        # No sentence boundaries — split at word boundary
        return _split_at_words(text, max_len)

    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current} {part}" if current else part
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            if len(part) <= max_len:
                current = part
            else:
                chunks.extend(_split_at_words(part, max_len))
                current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _split_at_words(text: str, max_len: int) -> list[str]:
    """Last resort — split at word boundaries."""
    words = text.split(" ")
    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            current = word
    if current.strip():
        chunks.append(current.strip())
    return chunks


# ── Agent resolution with IGSID self-healing ────────────────────────

# In-memory cache: webhook IGSID → DB ig_user_id
_igsid_cache: dict[str, str] = {}


async def _resolve_agent(
    db: AsyncSession, webhook_ig_id: str, sender_ig_id: str
) -> tuple[Agent | None, InstagramAccount | None]:
    """Find the correct agent for a webhook event.

    NEVER falls back to a different account. If the correct account
    can't be found or its agent is inactive, returns (None, None).

    Resolution strategy:
    1. Direct match on ig_user_id (works after IGSID is stored)
    2. In-memory cache lookup
    3. Call /me?fields=user_id with ALL accounts to discover the mapping
    """
    if not webhook_ig_id:
        logger.warning("No webhook_ig_id — cannot route message from %s", sender_ig_id)
        return None, None

    # Strategy 1: Direct match (active agent required)
    result = await db.execute(
        select(Agent, InstagramAccount)
        .join(InstagramAccount)
        .where(
            Agent.is_active.is_(True),
            InstagramAccount.ig_user_id == webhook_ig_id,
        )
        .limit(1)
    )
    row = result.first()
    if row:
        return row[0], row[1]

    # Strategy 2: Cache lookup (active agent required)
    if webhook_ig_id in _igsid_cache:
        cached_id = _igsid_cache[webhook_ig_id]
        result = await db.execute(
            select(Agent, InstagramAccount)
            .join(InstagramAccount)
            .where(
                Agent.is_active.is_(True),
                InstagramAccount.ig_user_id == cached_id,
            )
            .limit(1)
        )
        row = result.first()
        if row:
            logger.info("Cache hit: webhook ID %s → DB ID %s", webhook_ig_id, cached_id)
            return row[0], row[1]
        else:
            # Cache entry exists but agent is now inactive
            logger.info("⏭️ Cached account %s has no active agent — skipping", cached_id)
            return None, None

    # Strategy 3: Resolve by calling /me with ALL IG accounts (not just active)
    all_accounts_result = await db.execute(select(InstagramAccount))
    all_accounts = all_accounts_result.scalars().all()

    for ig_account in all_accounts:
        if not ig_account.page_access_token:
            continue
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "https://graph.instagram.com/v25.0/me",
                    params={
                        "fields": "user_id",
                        "access_token": ig_account.page_access_token,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data and isinstance(data["data"], list) and data["data"]:
                        igsid = str(data["data"][0].get("user_id", ""))
                    else:
                        igsid = str(data.get("user_id", ""))

                    if igsid == webhook_ig_id:
                        # Found the mapping — cache it
                        _igsid_cache[webhook_ig_id] = ig_account.ig_user_id
                        logger.info(
                            "✅ Resolved: webhook ID %s → @%s (DB ID %s)",
                            webhook_ig_id, ig_account.ig_username, ig_account.ig_user_id,
                        )

                        # Now find the ACTIVE agent for this specific account
                        agent_result = await db.execute(
                            select(Agent).where(
                                Agent.instagram_account_id == ig_account.id,
                                Agent.is_active.is_(True),
                            ).limit(1)
                        )
                        agent = agent_result.scalar_one_or_none()

                        if not agent:
                            logger.info(
                                "⏭️ @%s matched but agent is disabled — skipping",
                                ig_account.ig_username,
                            )
                            return None, None

                        return agent, ig_account
                else:
                    logger.debug("/me failed for @%s: %s", ig_account.ig_username, resp.text)
        except Exception:
            logger.debug("/me request failed for @%s", ig_account.ig_username, exc_info=True)

    logger.warning(
        "Could not resolve webhook ID %s to any IG account — ignoring message from %s",
        webhook_ig_id, sender_ig_id,
    )
    return None, None

