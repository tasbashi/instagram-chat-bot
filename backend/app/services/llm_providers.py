"""Extensible LLM provider registry.

Each provider defines its identity, required config fields, and how to
build an HTTP request from a config dict.  Adding a new provider is a
single dict entry — no code changes elsewhere.

Usage:
    from app.services.llm_providers import PROVIDERS, get_provider

    provider = get_provider("groq")
    request_params = provider.build_request(decrypted_config)
    # → {"url": "...", "headers": {...}, "model": "..."}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ProviderField:
    """Describes one config field for a provider."""
    key: str
    label: str
    type: str = "text"          # "text" | "password" | "select"
    required: bool = True
    secret: bool = False        # True → encrypted in DB, masked in responses
    placeholder: str = ""
    help_text: str = ""
    options: list[dict[str, str]] = field(default_factory=list)  # For "select" type
    default: str = ""


@dataclass(frozen=True)
class LLMProvider:
    """One LLM provider definition."""
    id: str
    name: str
    description: str
    fields: list[ProviderField]
    build_request: Callable[[dict[str, Any]], dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Serialize for the /api/llm-providers endpoint."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "type": f.type,
                    "required": f.required,
                    "secret": f.secret,
                    "placeholder": f.placeholder,
                    "help_text": f.help_text,
                    "options": f.options,
                    "default": f.default,
                }
                for f in self.fields
            ],
        }


# ── Provider builders ───────────────────────────────────────────────


def _build_azure_request(config: dict[str, Any]) -> dict[str, Any]:
    endpoint = config["endpoint"].rstrip("/")
    deployment = config["deployment_name"]
    api_version = config.get("api_version", "2024-08-01-preview")
    api_key = config["api_key"]

    url = (
        f"{endpoint}/openai/deployments/{deployment}"
        f"/chat/completions?api-version={api_version}"
    )
    return {
        "url": url,
        "headers": {
            "Content-Type": "application/json",
            "api-key": api_key,
        },
        "model": deployment,
        "provider": "azure_openai",
        "model_in_body": False,  # Azure puts model in URL
    }


def _build_groq_request(config: dict[str, Any]) -> dict[str, Any]:
    api_key = config["api_key"]
    model = config.get("model", "llama-3.3-70b-versatile")

    return {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        "model": model,
        "provider": "groq",
        "model_in_body": True,
    }


# ── Registry ────────────────────────────────────────────────────────


PROVIDERS: dict[str, LLMProvider] = {
    "azure_openai": LLMProvider(
        id="azure_openai",
        name="Azure OpenAI",
        description="Microsoft Azure-hosted OpenAI models (GPT-4o, GPT-4, etc.)",
        fields=[
            ProviderField(
                key="endpoint",
                label="Endpoint URL",
                placeholder="https://your-resource.openai.azure.com",
                help_text="Your Azure OpenAI resource endpoint",
            ),
            ProviderField(
                key="api_key",
                label="API Key",
                type="password",
                secret=True,
                placeholder="your-azure-api-key",
            ),
            ProviderField(
                key="deployment_name",
                label="Deployment Name",
                placeholder="gpt-4o",
                help_text="The name of your model deployment",
            ),
            ProviderField(
                key="api_version",
                label="API Version",
                required=False,
                placeholder="2024-08-01-preview",
                default="2024-08-01-preview",
                help_text="Azure OpenAI API version",
            ),
        ],
        build_request=_build_azure_request,
    ),
    "groq": LLMProvider(
        id="groq",
        name="Groq",
        description="Ultra-fast inference with Groq LPU (Llama, Mixtral, etc.)",
        fields=[
            ProviderField(
                key="api_key",
                label="API Key",
                type="password",
                secret=True,
                placeholder="gsk_...",
            ),
            ProviderField(
                key="model",
                label="Model",
                type="select",
                placeholder="llama-3.3-70b-versatile",
                default="llama-3.3-70b-versatile",
                options=[
                    {"value": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B"},
                    {"value": "llama-3.1-8b-instant", "label": "Llama 3.1 8B"},
                    {"value": "mixtral-8x7b-32768", "label": "Mixtral 8x7B"},
                    {"value": "gemma2-9b-it", "label": "Gemma 2 9B"},
                ],
            ),
        ],
        build_request=_build_groq_request,
    ),
}


def get_provider(provider_id: str) -> LLMProvider:
    """Get a provider by ID. Raises ValueError if not found."""
    provider = PROVIDERS.get(provider_id)
    if not provider:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown LLM provider: '{provider_id}'. Available: {available}")
    return provider


def list_providers() -> list[dict[str, Any]]:
    """Return all providers serialized for the API."""
    return [p.to_dict() for p in PROVIDERS.values()]


def get_secret_fields(provider_id: str) -> list[str]:
    """Return the keys of fields that are marked as secret for a provider."""
    provider = PROVIDERS.get(provider_id)
    if not provider:
        return []
    return [f.key for f in provider.fields if f.secret]
