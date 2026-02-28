"""LLM client — supports Groq and Azure OpenAI via an extensible provider registry.

Both use OpenAI-compatible chat completions format, so the response
parsing is shared. Provider is determined per-agent via llm_config,
with fallback to global settings.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import settings
from app.services.encryption import decrypt
from app.services.llm_providers import get_provider, get_secret_fields

logger = logging.getLogger("llm_client")


# ── Provider config resolution ──────────────────────────────────────


def _resolve_request_params(llm_config: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve URL, headers, and model for the request.

    Uses per-agent llm_config if it has a provider + provider_config with
    the required fields. Falls back to global settings otherwise.
    """
    if llm_config:
        provider_id = llm_config.get("provider")
        provider_config = llm_config.get("provider_config", {})

        if provider_id and provider_config:
            try:
                provider = get_provider(provider_id)

                # Decrypt secret fields before building the request
                decrypted_config = dict(provider_config)
                for key in get_secret_fields(provider_id):
                    if key in decrypted_config and decrypted_config[key]:
                        decrypted_config[key] = decrypt(decrypted_config[key])

                # Check all required fields are present
                required_keys = [f.key for f in provider.fields if f.required]
                if all(decrypted_config.get(k) for k in required_keys):
                    return provider.build_request(decrypted_config)
            except (ValueError, KeyError) as exc:
                logger.warning("Per-agent provider config failed: %s — falling back to global", exc)

    # Fallback: use global settings
    return _get_global_provider_config()


def _get_global_provider_config() -> dict[str, Any]:
    """Resolve URL, headers, and model from global .env settings."""
    provider = settings.llm_provider.lower()

    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is empty. Set it in .env.")
        return {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.groq_api_key}",
            },
            "model": settings.groq_model,
            "provider": "groq",
            "model_in_body": True,
        }
    elif provider == "azure":
        if not settings.azure_openai_api_key:
            raise RuntimeError("AZURE_OPENAI_API_KEY is empty. Set it in .env.")
        url = (
            f"{settings.azure_openai_endpoint.rstrip('/')}"
            f"/openai/deployments/{settings.azure_openai_model}/chat/completions"
            f"?api-version={settings.azure_openai_api_version}"
        )
        return {
            "url": url,
            "headers": {
                "Content-Type": "application/json",
                "api-key": settings.azure_openai_api_key,
            },
            "model": settings.azure_openai_model,
            "provider": "azure",
            "model_in_body": False,
        }
    else:
        raise RuntimeError(f"Unknown global LLM provider: {provider}. Use 'groq' or 'azure'.")


# ── Public API ──────────────────────────────────────────────────────


async def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    llm_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the active LLM provider with optional function calling.

    If llm_config is provided (per-agent overrides), those values take
    precedence over the global settings.

    Returns the full response dict (OpenAI-compatible format).
    """
    pc = _resolve_request_params(llm_config)

    body: dict[str, Any] = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # Some providers need model in body, others put it in the URL
    if pc.get("model_in_body", True):
        body["model"] = pc["model"]

    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    logger.info("LLM request → %s (%s)", pc["provider"], pc["model"])

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(pc["url"], headers=pc["headers"], json=body)

    if resp.status_code != 200:
        logger.error("%s error (%s): %s", pc["provider"], resp.status_code, resp.text[:500])
        raise RuntimeError(f"{pc['provider']} API error: {resp.status_code}")

    data = resp.json()
    return data


def extract_response(data: dict[str, Any]) -> dict[str, Any]:
    """Extract the assistant's message from the API response.

    Returns dict with:
      - content: str | None (text response)
      - tool_calls: list[dict] | None (function calls requested)
    """
    choice = data["choices"][0]
    message = choice["message"]

    return {
        "content": message.get("content"),
        "tool_calls": message.get("tool_calls"),
        "finish_reason": choice.get("finish_reason"),
    }


def parse_tool_call_args(tool_call: dict[str, Any]) -> dict[str, Any]:
    """Parse the arguments JSON from a tool call."""
    args_str = tool_call["function"]["arguments"]
    try:
        return json.loads(args_str)
    except json.JSONDecodeError:
        logger.warning("Failed to parse tool call args: %s", args_str)
        return {}
