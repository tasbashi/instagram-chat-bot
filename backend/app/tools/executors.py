"""Tool implementations — search_knowledge, manage_appointment, send_email, collect_compliment."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import date, datetime, time, timezone
from typing import Any

from app.tools.base import BaseTool

logger = logging.getLogger("tools")


def _json(obj: Any) -> str:
    """JSON serialize with ensure_ascii=False to preserve Turkish/Unicode chars."""
    return json.dumps(obj, ensure_ascii=False)


async def _update_conversation_result(conversation_id: str | None, result: str) -> None:
    """Set the result column on a conversation record."""
    if not conversation_id:
        return
    try:
        from sqlalchemy import update
        from app.db.session import async_session_factory
        from app.models.conversation import Conversation

        async with async_session_factory() as db:
            await db.execute(
                update(Conversation)
                .where(Conversation.id == uuid.UUID(conversation_id))
                .values(result=result)
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to update conversation result")


# ═══════════════════════════════════════════════════════════════════
# SEARCH KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════


class SearchKnowledgeTool(BaseTool):
    name = "search_knowledge"
    description = (
        "Search the business knowledge base for information relevant to the "
        "customer's question. Use this for product details, pricing, business "
        "hours, policies, services offered, FAQs, etc."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query derived from the customer's question",
            },
        },
        "required": ["query"],
    }

    async def execute(self, args: dict[str, Any], context: dict[str, Any]) -> str:
        from app.services.rag.embedder import embed_query
        from app.services.rag.vector_store import search_vectors

        agent_id = context["agent_id"]
        query = args.get("query", "")

        if not query:
            return _json({"error": "Empty query"})

        try:
            query_vector = await embed_query(query)
            results = await search_vectors(
                agent_id=agent_id,
                query_vector=query_vector,
                top_k=5,
            )

            if not results:
                return _json({
                    "result_count": 0,
                    "message": "No relevant information found in the knowledge base.",
                })

            formatted = []
            for r in results:
                payload = r["payload"]
                formatted.append({
                    "text": payload.get("chunk_text", ""),
                    "section": payload.get("section_title", ""),
                    "source": payload.get("filename", ""),
                    "score": round(r["score"], 3),
                })

            return _json({
                "result_count": len(formatted),
                "results": formatted,
            })
        except Exception as exc:
            logger.exception("Knowledge search failed")
            return _json({"error": str(exc)})


# ═══════════════════════════════════════════════════════════════════
# MANAGE APPOINTMENT
# ═══════════════════════════════════════════════════════════════════


class ManageAppointmentTool(BaseTool):
    name = "manage_appointment"
    description = (
        "Manage appointments for the customer. Available actions:\n"
        "- 'check_availability': Check if a specific date/time is available. "
        "Returns booked slots and suggests alternative free times. "
        "ALWAYS check availability before creating an appointment.\n"
        "- 'create': Book a new appointment. Requires customer_name, customer_surname, "
        "date, time, and subject. Ask the customer for all required information before calling.\n"
        "- 'cancel': Cancel an existing appointment by ID.\n"
        "- 'list': Show the customer's upcoming appointments."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check_availability", "create", "cancel", "list"],
                "description": "The action to perform",
            },
            "date": {
                "type": "string",
                "description": "Appointment date in YYYY-MM-DD format (for check_availability and create)",
            },
            "time": {
                "type": "string",
                "description": "Appointment time in HH:MM 24h format (for create)",
            },
            "customer_name": {
                "type": "string",
                "description": "Customer's first name (required for create)",
            },
            "customer_surname": {
                "type": "string",
                "description": "Customer's surname / last name (required for create)",
            },
            "subject": {
                "type": "string",
                "description": "Subject / reason for the appointment (required for create)",
            },
            "service_type": {
                "type": "string",
                "description": "Type of service (for create)",
            },
            "duration_minutes": {
                "type": "integer",
                "description": "Duration of the appointment in minutes (default 30)",
            },
            "appointment_id": {
                "type": "string",
                "description": "Appointment ID (required for cancel)",
            },
            "notes": {
                "type": "string",
                "description": "Additional notes",
            },
        },
        "required": ["action"],
    }

    async def execute(self, args: dict[str, Any], context: dict[str, Any]) -> str:
        from sqlalchemy import select
        from app.db.session import async_session_factory
        from app.models.appointment import Appointment

        action = args.get("action", "list")
        agent_id = context["agent_id"]
        customer_ig_id = context["customer_ig_id"]

        async with async_session_factory() as db:
            try:
                if action == "check_availability":
                    return await self._check_availability(args, db, agent_id)
                elif action == "create":
                    result = await self._create(args, db, agent_id, customer_ig_id, context)
                elif action == "cancel":
                    result = await self._cancel(args, db, agent_id, customer_ig_id, context)
                elif action == "list":
                    return await self._list(db, agent_id, customer_ig_id)
                else:
                    return _json({"error": f"Unknown action: {action}"})
                return result
            except Exception as exc:
                logger.exception("Appointment tool failed")
                return _json({"error": str(exc)})

    async def _check_availability(
        self, args: dict, db: Any, agent_id: str
    ) -> str:
        """Check availability for a given date. Returns busy slots and suggests free ones."""
        from sqlalchemy import select, and_
        from app.models.appointment import Appointment

        date_str = args.get("date", "")
        if not date_str:
            return _json({"error": "Date is required for checking availability"})

        try:
            check_date = date.fromisoformat(date_str)
        except ValueError:
            return _json({"error": "Invalid date format. Use YYYY-MM-DD"})

        # Check if date is in the past
        if check_date < date.today():
            return _json({"error": "Cannot check availability for past dates"})

        # Query all confirmed appointments on this date for this agent
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.agent_id == uuid.UUID(agent_id),
                    Appointment.appointment_date == check_date,
                    Appointment.status.in_(["confirmed", "completed"]),
                )
            ).order_by(Appointment.appointment_time)
        )
        existing = result.scalars().all()

        booked_slots = []
        busy_minutes: list[tuple[int, int]] = []  # (start_min, end_min)

        for appt in existing:
            start_h = appt.appointment_time.hour
            start_m = appt.appointment_time.minute
            start_min = start_h * 60 + start_m
            end_min = start_min + (appt.duration_minutes or 30)
            busy_minutes.append((start_min, end_min))
            booked_slots.append({
                "time": f"{start_h:02d}:{start_m:02d}",
                "end_time": f"{end_min // 60:02d}:{end_min % 60:02d}",
                "duration": appt.duration_minutes or 30,
                "service_type": appt.service_type,
            })

        # Generate available 30-min slots between 09:00 and 18:00
        available_slots = []
        for hour in range(9, 18):
            for minute in [0, 30]:
                slot_start = hour * 60 + minute
                slot_end = slot_start + 30
                # Check if this slot overlaps with any existing appointment
                is_free = all(
                    slot_end <= bs or slot_start >= be
                    for bs, be in busy_minutes
                )
                if is_free:
                    available_slots.append(f"{hour:02d}:{minute:02d}")

        if not booked_slots:
            return _json({
                "date": date_str,
                "status": "fully_available",
                "message": f"No appointments on {date_str}. All time slots are available.",
                "available_slots": available_slots,
            })

        return _json({
            "date": date_str,
            "status": "partially_booked",
            "booked_count": len(booked_slots),
            "booked_slots": booked_slots,
            "available_slots": available_slots,
            "message": (
                f"There are {len(booked_slots)} appointment(s) on {date_str}. "
                f"{len(available_slots)} time slots are still available."
            ),
        })

    async def _create(
        self, args: dict, db: Any, agent_id: str, customer_ig_id: str, context: dict
    ) -> str:
        from sqlalchemy import select, and_
        from app.models.appointment import Appointment

        date_str = args.get("date", "")
        time_str = args.get("time", "")
        customer_name = args.get("customer_name", "").strip()
        customer_surname = args.get("customer_surname", "").strip()
        subject_val = args.get("subject", "").strip()

        # Reject placeholder / dummy values the LLM might fill in
        _placeholders = {"required", "unknown", "n/a", "none", "tbd", "null", "undefined", "customer", "name", "surname", "subject", ""}
        
        if customer_name.lower() in _placeholders:
            return _json({"error": "You do NOT have the customer's real name yet. You MUST ask the customer: 'What is your first name?' and wait for their reply before calling this tool."})

        if customer_surname.lower() in _placeholders:
            return _json({"error": "You do NOT have the customer's real surname yet. You MUST ask the customer: 'What is your surname?' and wait for their reply before calling this tool."})

        if subject_val.lower() in _placeholders:
            return _json({"error": "You do NOT have the appointment subject yet. You MUST ask the customer: 'What is the reason/subject for your appointment?' and wait for their reply before calling this tool."})

        if not date_str or not time_str:
            return _json({"error": "Date and time are required for creating an appointment. Ask the customer which date and time they prefer."})

        try:
            appt_date = date.fromisoformat(date_str)
            parts = time_str.split(":")
            appt_time = time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return _json({"error": "Invalid date or time format"})

        if appt_date < date.today():
            return _json({"error": "Cannot create appointments in the past"})

        duration = args.get("duration_minutes", 30)

        # Check for conflicts before creating
        new_start = appt_time.hour * 60 + appt_time.minute
        new_end = new_start + duration

        conflict_result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.agent_id == uuid.UUID(agent_id),
                    Appointment.appointment_date == appt_date,
                    Appointment.status == "confirmed",
                )
            )
        )
        conflicts = conflict_result.scalars().all()

        for existing in conflicts:
            ex_start = existing.appointment_time.hour * 60 + existing.appointment_time.minute
            ex_end = ex_start + (existing.duration_minutes or 30)
            if new_start < ex_end and new_end > ex_start:
                # Time conflict found — suggest alternatives
                # Find free slots on same day
                busy = [(existing.appointment_time.hour * 60 + existing.appointment_time.minute,
                         existing.appointment_time.hour * 60 + existing.appointment_time.minute + (existing.duration_minutes or 30))
                        for existing in conflicts]
                alternatives = []
                for h in range(9, 18):
                    for m in [0, 30]:
                        s = h * 60 + m
                        e = s + duration
                        if all(e <= bs or s >= be for bs, be in busy):
                            alternatives.append(f"{h:02d}:{m:02d}")
                            if len(alternatives) >= 5:
                                break
                    if len(alternatives) >= 5:
                        break

                return _json({
                    "error": "time_conflict",
                    "message": f"The requested time {time_str} on {date_str} conflicts with an existing appointment.",
                    "suggested_alternatives": alternatives,
                    "suggestion_message": (
                        f"The following times are available on {date_str}: "
                        + ", ".join(alternatives)
                    ) if alternatives else f"No available slots on {date_str}. Please try another date.",
                })

        # Resolve owner user_id from agent
        from app.models.agent import Agent
        from app.models.instagram_account import InstagramAccount
        agent_result = await db.execute(
            select(InstagramAccount.user_id)
            .join(Agent, Agent.instagram_account_id == InstagramAccount.id)
            .where(Agent.id == uuid.UUID(agent_id))
            .limit(1)
        )
        owner_user_id = agent_result.scalar_one_or_none()

        appointment = Appointment(
            agent_id=uuid.UUID(agent_id),
            user_id=owner_user_id,
            customer_ig_id=customer_ig_id,
            customer_name=customer_name,
            customer_surname=customer_surname,
            appointment_date=appt_date,
            appointment_time=appt_time,
            duration_minutes=duration,
            service_type=args.get("service_type"),
            subject=subject_val,
            notes=args.get("notes"),
            created_via="chatbot",
        )
        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        appt_data = {
            "status": "confirmed",
            "appointment_id": str(appointment.id),
            "customer_name": appointment.customer_name,
            "customer_surname": appointment.customer_surname,
            "date": str(appointment.appointment_date),
            "time": str(appointment.appointment_time),
            "subject": appointment.subject,
            "service_type": appointment.service_type,
        }

        # Fire-and-forget: email notification to owner
        from app.services.email_service import notify_appointment_created
        asyncio.create_task(notify_appointment_created(agent_id, appt_data))

        # Update conversation result
        asyncio.create_task(_update_conversation_result(context.get("conversation_id"), "appointment_created"))

        return _json(appt_data)

    async def _cancel(self, args: dict, db: Any, agent_id: str, customer_ig_id: str, context: dict) -> str:
        from sqlalchemy import select
        from app.models.appointment import Appointment

        appt_id = args.get("appointment_id")
        if not appt_id:
            return _json({"error": "appointment_id is required for cancellation"})

        try:
            appt_uuid = uuid.UUID(appt_id)
        except ValueError:
            return _json({"error": "Invalid appointment_id format. Use the 'list' action first to get the customer's appointment IDs, then use the exact ID to cancel."})

        result = await db.execute(
            select(Appointment).where(
                Appointment.id == appt_uuid,
                Appointment.agent_id == uuid.UUID(agent_id),
                Appointment.customer_ig_id == customer_ig_id,
            )
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            return _json({"error": "Appointment not found"})

        cancel_data = {
            "customer_name": appointment.customer_name,
            "customer_surname": appointment.customer_surname,
            "date": str(appointment.appointment_date),
            "time": str(appointment.appointment_time),
            "reason": args.get("notes", "Cancelled via chatbot"),
        }

        appointment.status = "cancelled"
        appointment.cancelled_at = datetime.now(timezone.utc)
        appointment.cancellation_reason = args.get("notes", "Cancelled via chatbot")
        await db.commit()

        # Fire-and-forget: email notification to owner
        if appointment.agent_id:
            from app.services.email_service import notify_appointment_cancelled
            asyncio.create_task(notify_appointment_cancelled(str(appointment.agent_id), cancel_data))

        # Update conversation result
        asyncio.create_task(_update_conversation_result(context.get("conversation_id"), "appointment_cancelled"))

        return _json({
            "status": "cancelled",
            "appointment_id": str(appointment.id),
        })

    async def _list(self, db: Any, agent_id: str, customer_ig_id: str) -> str:
        from sqlalchemy import select
        from app.models.appointment import Appointment

        result = await db.execute(
            select(Appointment)
            .where(
                Appointment.agent_id == uuid.UUID(agent_id),
                Appointment.customer_ig_id == customer_ig_id,
                Appointment.status == "confirmed",
                Appointment.appointment_date >= date.today(),
            )
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
        )
        appointments = result.scalars().all()

        if not appointments:
            return _json({
                "count": 0,
                "message": "No upcoming appointments found.",
            })

        items = [
            {
                "id": str(a.id),
                "date": str(a.appointment_date),
                "time": str(a.appointment_time),
                "customer_name": a.customer_name,
                "customer_surname": a.customer_surname,
                "subject": a.subject,
                "service_type": a.service_type,
                "notes": a.notes,
            }
            for a in appointments
        ]

        return _json({"count": len(items), "appointments": items})


# ═══════════════════════════════════════════════════════════════════
# SEND EMAIL
# ═══════════════════════════════════════════════════════════════════


class SendEmailTool(BaseTool):
    name = "send_email"
    description = (
        "Send an email to the business owner or a specified address. "
        "Use for appointment confirmations, detailed information requests, "
        "escalations, or forwarding customer inquiries."
    )
    parameters = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address",
            },
            "subject": {
                "type": "string",
                "description": "Email subject line",
            },
            "body": {
                "type": "string",
                "description": "Email body content",
            },
        },
        "required": ["to", "subject", "body"],
    }

    async def execute(self, args: dict[str, Any], context: dict[str, Any]) -> str:
        from app.services.email_service import send_email
        from app.db.session import async_session_factory
        from app.models.email_log import EmailLog

        to = args.get("to", "")
        subject = args.get("subject", "")
        body = args.get("body", "")

        success = await send_email(to=to, subject=subject, body=body)

        # Log to database
        async with async_session_factory() as db:
            log = EmailLog(
                agent_id=uuid.UUID(context["agent_id"]),
                conversation_id=uuid.UUID(context["conversation_id"]) if context.get("conversation_id") else None,
                recipient_email=to,
                subject=subject,
                body=body,
                status="sent" if success else "failed",
            )
            db.add(log)
            await db.commit()

        if success:
            return _json({"status": "sent", "to": to, "subject": subject})
        return _json({"status": "failed", "error": "Email sending failed"})


# ═══════════════════════════════════════════════════════════════════
# COLLECT COMPLIMENT
# ═══════════════════════════════════════════════════════════════════


class CollectComplimentTool(BaseTool):
    name = "collect_compliment"
    description = (
        "Record a positive customer remark, compliment, or feedback. "
        "Use this when the customer says something positive about the business, "
        "service, or product."
    )
    parameters = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The compliment text from the customer",
            },
        },
        "required": ["content"],
    }

    async def execute(self, args: dict[str, Any], context: dict[str, Any]) -> str:
        from app.db.session import async_session_factory
        from app.models.compliment import Compliment

        content = args.get("content", "")

        async with async_session_factory() as db:
            compliment = Compliment(
                agent_id=uuid.UUID(context["agent_id"]),
                conversation_id=uuid.UUID(context["conversation_id"]) if context.get("conversation_id") else None,
                customer_ig_id=context["customer_ig_id"],
                content=content,
            )
            db.add(compliment)
            await db.commit()

        # Fire-and-forget: email notification to owner
        from app.services.email_service import notify_compliment_received
        asyncio.create_task(notify_compliment_received(
            context["agent_id"],
            {"customer_ig_id": context["customer_ig_id"], "content": content},
        ))

        # Update conversation result
        asyncio.create_task(_update_conversation_result(context.get("conversation_id"), "compliment"))

        return _json({"status": "recorded", "content": content})


# ═══════════════════════════════════════════════════════════════════
# REGISTRY FACTORY
# ═══════════════════════════════════════════════════════════════════


def create_tool_registry() -> "ToolRegistry":
    """Create and populate the default tool registry."""
    from app.tools.base import ToolRegistry

    registry = ToolRegistry()
    registry.register(SearchKnowledgeTool())
    registry.register(ManageAppointmentTool())
    registry.register(SendEmailTool())
    registry.register(CollectComplimentTool())
    return registry
