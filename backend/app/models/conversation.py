"""Conversation model — tracks a chat session between agent and customer."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
    )
    customer_ig_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_username: Mapped[str | None] = mapped_column(String(255))
    customer_profile_pic: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active | resolved | escalated
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[str | None] = mapped_column(
        String(100)
    )  # appointment_created | appointment_cancelled | compliment | email_sent | knowledge_used
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    # Relationships
    agent: Mapped["Agent | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.customer_ig_id} [{self.status}]>"
