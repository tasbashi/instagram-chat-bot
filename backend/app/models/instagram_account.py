"""Instagram Account model — linked via OAuth."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ig_user_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    ig_username: Mapped[str] = mapped_column(String(255), nullable=False)
    page_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="instagram_accounts")
    agent: Mapped["Agent | None"] = relationship(
        back_populates="instagram_account", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<InstagramAccount @{self.ig_username}>"
