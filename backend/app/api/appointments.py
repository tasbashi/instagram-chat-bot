"""Appointment routes — list, create, cancel, complete."""

from __future__ import annotations

import uuid as uuid_mod
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, DBSession
from app.models.agent import Agent
from app.models.appointment import Appointment
from app.models.instagram_account import InstagramAccount
from app.schemas import AppointmentCancel, AppointmentCreate, AppointmentOut, AppointmentUpdate

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.get("")
async def list_appointments(
    db: DBSession,
    current_user: CurrentUser,
    agent_id: Annotated[uuid_mod.UUID | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[AppointmentOut]:
    # Build query scoped to user's agents
    user_agent_ids = (
        select(Agent.id)
        .join(InstagramAccount)
        .where(InstagramAccount.user_id == current_user.id)
    )

    query = select(Appointment).where(Appointment.agent_id.in_(user_agent_ids))

    if agent_id:
        query = query.where(Appointment.agent_id == agent_id)
    if status_filter:
        query = query.where(Appointment.status == status_filter)
    if date_from:
        query = query.where(Appointment.appointment_date >= date_from)
    if date_to:
        query = query.where(Appointment.appointment_date <= date_to)

    query = query.order_by(
        Appointment.appointment_date.desc(), Appointment.appointment_time.desc()
    )

    result = await db.execute(query)
    appointments = result.scalars().all()
    return [AppointmentOut.model_validate(a) for a in appointments]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreate, db: DBSession, current_user: CurrentUser
) -> AppointmentOut:
    # Verify agent ownership if provided
    if body.agent_id:
        agent = await _verify_agent_ownership(body.agent_id, db, current_user)

    appointment = Appointment(
        agent_id=body.agent_id,
        customer_ig_id=body.customer_ig_id,
        customer_name=body.customer_name,
        customer_surname=body.customer_surname,
        appointment_date=body.appointment_date,
        appointment_time=body.appointment_time,
        duration_minutes=body.duration_minutes,
        service_type=body.service_type,
        subject=body.subject,
        notes=body.notes,
        created_via="manual",
    )
    db.add(appointment)
    await db.flush()
    await db.refresh(appointment)
    return AppointmentOut.model_validate(appointment)


@router.put("/{appointment_id}")
async def update_appointment(
    appointment_id: uuid_mod.UUID,
    body: AppointmentUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> AppointmentOut:
    appointment = await _get_user_appointment(appointment_id, db, current_user)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)

    await db.flush()
    await db.refresh(appointment)
    return AppointmentOut.model_validate(appointment)


@router.put("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: uuid_mod.UUID,
    body: AppointmentCancel,
    db: DBSession,
    current_user: CurrentUser,
) -> AppointmentOut:
    appointment = await _get_user_appointment(appointment_id, db, current_user)
    appointment.status = "cancelled"
    appointment.cancelled_at = datetime.now(timezone.utc)
    appointment.cancellation_reason = body.cancellation_reason
    await db.flush()
    await db.refresh(appointment)
    return AppointmentOut.model_validate(appointment)


@router.put("/{appointment_id}/complete")
async def complete_appointment(
    appointment_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> AppointmentOut:
    appointment = await _get_user_appointment(appointment_id, db, current_user)
    appointment.status = "completed"
    await db.flush()
    await db.refresh(appointment)
    return AppointmentOut.model_validate(appointment)


# ── Helpers ──────────────────────────────────────────────────────────


async def _verify_agent_ownership(
    agent_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> Agent:
    result = await db.execute(
        select(Agent)
        .join(InstagramAccount)
        .where(Agent.id == agent_id, InstagramAccount.user_id == current_user.id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


async def _get_user_appointment(
    appointment_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> Appointment:
    user_agent_ids = (
        select(Agent.id)
        .join(InstagramAccount)
        .where(InstagramAccount.user_id == current_user.id)
    )
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.agent_id.in_(user_agent_ids),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
        )
    return appointment
