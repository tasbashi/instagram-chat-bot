"""Agent model — one per Instagram account."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

DEFAULT_PERMISSIONS = {
    "read_messages": True,
    "write_messages": True,
    "send_email": False,
    "manage_appointments": False,
}

DEFAULT_LLM_CONFIG = {
    "temperature": 0.3,
    "max_tokens": 2048,
}


def _default_llm_config() -> dict:
    """Build LLM config from current settings so new agents use the active provider."""
    from app.config import settings
    return {
        "provider": settings.llm_provider,
        "provider_config": {},
        **DEFAULT_LLM_CONFIG,
    }


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instagram_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instagram_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_context: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[dict] = mapped_column(
        JSON, default=lambda: DEFAULT_PERMISSIONS.copy()
    )
    llm_config: Mapped[dict] = mapped_column(
        JSON, default=_default_llm_config
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    instagram_account: Mapped["InstagramAccount"] = relationship(
        back_populates="agent"
    )
    knowledge_documents: Mapped[list["KnowledgeDocument"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="agent"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="agent"
    )

    def __repr__(self) -> str:
        return f"<Agent {self.name}>"
