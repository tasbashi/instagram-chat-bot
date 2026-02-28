"""Centralised configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger("config")

load_dotenv()


class Settings(BaseSettings):
    # ── App ──
    port: int = 8000
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours
    encryption_key: str = ""
    frontend_url: str = "http://localhost:3000"

    # ── Database ──
    database_url: str = Field(
        default="postgresql+asyncpg://chatbot_user:chatbot_secure_2026@localhost:5432/instagram_chatbot"
    )

    # ── Qdrant ──
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # ── Instagram / Meta ──
    verify_token: str = "instagram_webhook_verify"
    page_access_token: str = ""
    app_secret: str = ""
    ngrok_auth_token: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    instagram_app_id: str = ""        # Instagram App ID (from Use Cases → API Setup)
    instagram_app_secret: str = ""    # Instagram App Secret
    backend_url: str = "http://localhost:8000"

    # ── LLM Provider ──
    llm_provider: str = "groq"  # "groq" | "azure"

    # ── Groq ──
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Azure OpenAI ──
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_model: str = "gpt-4o"
    azure_openai_api_version: str = "2024-08-01-preview"

    # ── Vertex AI (Embeddings) ──
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    embedding_model: str = "text-embedding-004"
    embedding_dimension: int = 768

    # ── Email (SMTP) ──
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # ── RAG ──
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 50

    # ── Uploads ──
    upload_dir: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "uploads"
    )

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("encryption_key", mode="before")
    @classmethod
    def _ensure_encryption_key(cls, v: str) -> str:
        if not v:
            key = Fernet.generate_key().decode()
            logger.warning(
                "ENCRYPTION_KEY not set — auto-generated. "
                "Set ENCRYPTION_KEY=%s in .env for persistence.",
                key,
            )
            return key
        return v


settings = Settings()
