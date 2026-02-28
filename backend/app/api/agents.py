"""Agent CRUD routes — create, list, update context/permissions, upload PDF."""

from __future__ import annotations

import logging
import os
import shutil
import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.deps import CurrentUser, DBSession
from app.models.agent import Agent
from app.models.instagram_account import InstagramAccount
from app.models.knowledge_document import KnowledgeDocument
from app.services.encryption import encrypt, decrypt
from app.services.llm_providers import get_provider, get_secret_fields, list_providers
from app.services.rag.vector_store import delete_by_document, delete_collection
from app.schemas import (
    AgentCreate,
    AgentLLMConfigUpdate,
    AgentOut,
    AgentPermissionsUpdate,
    AgentUpdate,
    KnowledgeDocumentOut,
    LlmProviderOut,
)
from app.services.rag.ingestion import ingest_pdf

logger = logging.getLogger("agents_api")

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ── LLM Providers ──────────────────────────────────────────────────


@router.get("/llm-providers", response_model=list[LlmProviderOut])
async def get_llm_providers() -> list[dict[str, Any]]:
    """Return the list of available LLM providers with their field schemas."""
    return list_providers()


# ── Agent CRUD ──────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate, db: DBSession, current_user: CurrentUser
) -> AgentOut:
    # Verify the IG account belongs to the current user
    result = await db.execute(
        select(InstagramAccount).where(
            InstagramAccount.id == body.instagram_account_id,
            InstagramAccount.user_id == current_user.id,
        )
    )
    ig_account = result.scalar_one_or_none()
    if not ig_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instagram account not found or not owned by you",
        )

    # Check if agent already exists for this account
    existing = await db.execute(
        select(Agent).where(Agent.instagram_account_id == body.instagram_account_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An agent already exists for this Instagram account",
        )

    # Build llm_config with encrypted secrets
    llm_config = _build_llm_config(
        provider=body.llm_provider,
        provider_config=body.llm_provider_config,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )

    agent = Agent(
        instagram_account_id=body.instagram_account_id,
        name=body.name,
        system_context=body.system_context,
        llm_config=llm_config,
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent, attribute_names=["instagram_account"])

    return AgentOut.from_agent(agent)


@router.get("")
async def list_agents(db: DBSession, current_user: CurrentUser) -> list[AgentOut]:
    result = await db.execute(
        select(Agent)
        .join(InstagramAccount)
        .where(InstagramAccount.user_id == current_user.id)
        .options(selectinload(Agent.instagram_account))
    )
    agents = result.scalars().all()
    return [AgentOut.from_agent(a) for a in agents]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> AgentOut:
    agent = await _get_user_agent(agent_id, db, current_user)
    return AgentOut.from_agent(agent)


@router.put("/{agent_id}")
async def update_agent(
    agent_id: uuid_mod.UUID, body: AgentUpdate, db: DBSession, current_user: CurrentUser
) -> AgentOut:
    agent = await _get_user_agent(agent_id, db, current_user)

    if body.name is not None:
        agent.name = body.name
    if body.system_context is not None:
        agent.system_context = body.system_context

    await db.flush()
    await db.refresh(agent)
    return AgentOut.from_agent(agent)


@router.put("/{agent_id}/permissions")
async def update_permissions(
    agent_id: uuid_mod.UUID,
    body: AgentPermissionsUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> AgentOut:
    agent = await _get_user_agent(agent_id, db, current_user)
    agent.permissions = body.model_dump()
    await db.flush()
    await db.refresh(agent)
    return AgentOut.from_agent(agent)


@router.put("/{agent_id}/toggle")
async def toggle_agent(
    agent_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> AgentOut:
    agent = await _get_user_agent(agent_id, db, current_user)
    agent.is_active = not agent.is_active
    await db.flush()
    await db.refresh(agent)
    return AgentOut.from_agent(agent)


@router.put("/{agent_id}/llm-config")
async def update_llm_config(
    agent_id: uuid_mod.UUID,
    body: AgentLLMConfigUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> AgentOut:
    agent = await _get_user_agent(agent_id, db, current_user)

    current_config = agent.llm_config or {}

    # Determine provider
    provider = body.provider or current_config.get("provider")

    # Handle provider_config: merge with existing, keeping encrypted values
    # for secret fields that weren't sent (i.e. the masked placeholder)
    new_provider_config = body.provider_config or {}
    existing_provider_config = current_config.get("provider_config", {})

    if provider:
        secret_keys = get_secret_fields(provider)
        merged_config: dict[str, Any] = {}

        # Start with existing config
        merged_config.update(existing_provider_config)

        # Apply new values, encrypting secrets
        for key, value in new_provider_config.items():
            if key in secret_keys and value:
                # Check if the value is a masked placeholder (contains •)
                if "•" in value:
                    # Keep the existing encrypted value
                    continue
                merged_config[key] = encrypt(value)
            else:
                merged_config[key] = value

        new_provider_config = merged_config

    agent.llm_config = {
        "provider": provider,
        "provider_config": new_provider_config,
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
    }

    await db.flush()
    await db.refresh(agent)
    return AgentOut.from_agent(agent)


# ── Knowledge Documents ─────────────────────────────────────────────


@router.post("/{agent_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    agent_id: uuid_mod.UUID,
    file: UploadFile,
    db: DBSession,
    current_user: CurrentUser,
) -> KnowledgeDocumentOut:
    agent = await _get_user_agent(agent_id, db, current_user)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    # Save file to disk
    agent_dir = os.path.join(settings.upload_dir, str(agent.id))
    os.makedirs(agent_dir, exist_ok=True)

    file_id = uuid_mod.uuid4()
    file_path = os.path.join(agent_dir, f"{file_id}_{file.filename}")
    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = KnowledgeDocument(
        agent_id=agent.id,
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=len(content),
        status="processing",
    )
    db.add(doc)
    await db.flush()

    # Trigger async ingestion (runs in background)
    try:
        result = await ingest_pdf(
            pdf_path=file_path,
            agent_id=str(agent.id),
            document_id=str(doc.id),
        )
        doc.page_count = result["page_count"]
        doc.chunk_count = result["chunk_count"]
        doc.status = "ready"
    except Exception as exc:
        logger.exception("PDF ingestion failed for %s", file.filename)
        doc.status = "error"
        doc.error_message = str(exc)

    await db.flush()
    return KnowledgeDocumentOut.model_validate(doc)


@router.get("/{agent_id}/documents")
async def list_documents(
    agent_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> list[KnowledgeDocumentOut]:
    agent = await _get_user_agent(agent_id, db, current_user)
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.agent_id == agent.id)
    )
    docs = result.scalars().all()
    return [KnowledgeDocumentOut.model_validate(d) for d in docs]


@router.delete("/{agent_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    agent_id: uuid_mod.UUID,
    doc_id: uuid_mod.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    agent = await _get_user_agent(agent_id, db, current_user)
    result = await db.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == doc_id,
            KnowledgeDocument.agent_id == agent.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Delete file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Delete vectors from Qdrant for this document
    try:
        await delete_by_document(str(agent.id), str(doc.id))
    except Exception:
        logger.warning("Failed to delete vectors for document %s", doc_id)

    await db.delete(doc)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid_mod.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    agent = await _get_user_agent(agent_id, db, current_user)

    # Delete Qdrant collection
    try:
        await delete_collection(str(agent.id))
    except Exception:
        logger.warning("Failed to delete Qdrant collection for agent %s", agent_id)

    # Delete document files from disk
    docs_dir = os.path.join(settings.upload_dir, str(agent.id))
    if os.path.exists(docs_dir):
        shutil.rmtree(docs_dir)

    await db.delete(agent)


# ── Helpers ──────────────────────────────────────────────────────────


def _build_llm_config(
    provider: str | None,
    provider_config: dict[str, Any] | None,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Build the llm_config dict, encrypting secret fields."""
    config: dict[str, Any] = {
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if provider:
        # Validate provider exists
        try:
            get_provider(provider)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        config["provider"] = provider

        # Encrypt secret fields
        if provider_config:
            secret_keys = get_secret_fields(provider)
            encrypted_config = dict(provider_config)
            for key in secret_keys:
                if key in encrypted_config and encrypted_config[key]:
                    encrypted_config[key] = encrypt(encrypted_config[key])
            config["provider_config"] = encrypted_config
        else:
            config["provider_config"] = {}
    else:
        # Use global defaults
        from app.config import settings as app_settings
        config["provider"] = app_settings.llm_provider
        config["provider_config"] = {}

    return config


async def _get_user_agent(
    agent_id: uuid_mod.UUID, db: DBSession, current_user: CurrentUser
) -> Agent:
    result = await db.execute(
        select(Agent)
        .join(InstagramAccount)
        .where(Agent.id == agent_id, InstagramAccount.user_id == current_user.id)
        .options(selectinload(Agent.instagram_account))
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent
