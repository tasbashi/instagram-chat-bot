"""Pydantic schemas for request/response validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ── Auth ────────────────────────────────────────────────────────────


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterOut(BaseModel):
    message: str
    email: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendCodeRequest(BaseModel):
    email: EmailStr


# ── Instagram Account ──────────────────────────────────────────────


class InstagramAccountOut(BaseModel):
    id: uuid.UUID
    ig_user_id: str
    ig_username: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Agent ───────────────────────────────────────────────────────────


class AgentCreate(BaseModel):
    instagram_account_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    system_context: str | None = None
    llm_provider: str | None = None
    llm_provider_config: dict[str, Any] | None = None
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=128, le=16384)


class AgentUpdate(BaseModel):
    name: str | None = None
    system_context: str | None = None


class AgentPermissionsUpdate(BaseModel):
    read_messages: bool = True
    write_messages: bool = True
    send_email: bool = False
    manage_appointments: bool = False


class AgentLLMConfigUpdate(BaseModel):
    provider: str | None = None
    provider_config: dict[str, Any] | None = None
    temperature: float = Field(default=0.3, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=128, le=16384)


class AgentOut(BaseModel):
    id: uuid.UUID
    instagram_account_id: uuid.UUID
    instagram_username: str | None = None
    name: str
    system_context: str | None
    permissions: dict
    llm_config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_agent(cls, agent: Any) -> "AgentOut":
        from app.services.encryption import decrypt, mask_secret
        from app.services.llm_providers import get_secret_fields

        data = cls.model_validate(agent)
        if hasattr(agent, "instagram_account") and agent.instagram_account:
            data.instagram_username = agent.instagram_account.ig_username

        # Mask secret fields in llm_config for API responses
        llm_cfg = dict(data.llm_config) if data.llm_config else {}
        provider_id = llm_cfg.get("provider", "")
        provider_config = llm_cfg.get("provider_config", {})
        if provider_config and provider_id:
            secret_keys = get_secret_fields(provider_id)
            masked_config = dict(provider_config)
            for key in secret_keys:
                if key in masked_config and masked_config[key]:
                    decrypted = decrypt(masked_config[key])
                    masked_config[key] = mask_secret(decrypted)
            llm_cfg["provider_config"] = masked_config
        data.llm_config = llm_cfg
        return data


# ── LLM Provider ───────────────────────────────────────────────────


class LlmProviderFieldOut(BaseModel):
    key: str
    label: str
    type: str
    required: bool
    secret: bool
    placeholder: str
    help_text: str
    options: list[dict[str, str]]
    default: str


class LlmProviderOut(BaseModel):
    id: str
    name: str
    description: str
    fields: list[LlmProviderFieldOut]


# ── Knowledge Document ─────────────────────────────────────────────


class KnowledgeDocumentOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    filename: str
    file_size_bytes: int | None
    page_count: int | None
    chunk_count: int | None
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Appointment ─────────────────────────────────────────────────────


class AppointmentCreate(BaseModel):
    agent_id: uuid.UUID | None = None
    customer_ig_id: str
    customer_name: str | None = None
    customer_surname: str | None = None
    appointment_date: date
    appointment_time: time
    duration_minutes: int = 30
    service_type: str | None = None
    subject: str | None = None
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    appointment_date: date | None = None
    appointment_time: time | None = None
    duration_minutes: int | None = None
    service_type: str | None = None
    subject: str | None = None
    notes: str | None = None


class AppointmentCancel(BaseModel):
    cancellation_reason: str | None = None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID | None
    customer_ig_id: str
    customer_name: str | None
    customer_surname: str | None = None
    appointment_date: date
    appointment_time: time
    duration_minutes: int
    service_type: str | None
    subject: str | None = None
    notes: str | None
    status: str
    created_via: str
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Conversation ────────────────────────────────────────────────────


class ConversationOut(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID | None
    customer_ig_id: str
    customer_username: str | None = None
    customer_profile_pic: str | None = None
    status: str
    started_at: datetime
    last_message_at: datetime
    message_count: int
    result: str | None = None
    resolved_at: datetime | None
    tags: list[str] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_conversation(cls, conv: Any) -> "ConversationOut":
        data = cls.model_validate(conv)
        meta = conv.metadata_ if hasattr(conv, "metadata_") and conv.metadata_ else {}
        data.tags = meta.get("tags", [])
        return data


class MessageOut(BaseModel):
    id: uuid.UUID
    sender_type: str
    content: str
    tool_calls: Any | None = None
    rag_context: Any | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailOut(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]


class ConversationStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(active|resolved|escalated)$")
