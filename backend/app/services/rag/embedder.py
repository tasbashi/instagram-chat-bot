"""Azure OpenAI embedding client.

Uses the text-embedding-3-small model via REST API.
Supports configurable dimensions (default 768 to match existing Qdrant collections).
"""

from __future__ import annotations

import logging
from typing import Sequence

import httpx

from app.config import settings

logger = logging.getLogger("rag.embedder")


def _build_url() -> str:
    """Build the Azure OpenAI embeddings endpoint URL."""
    endpoint = settings.azure_embedding_endpoint.rstrip("/")
    deployment = settings.azure_embedding_deployment
    api_version = settings.azure_embedding_api_version
    return (
        f"{endpoint}/openai/deployments/{deployment}"
        f"/embeddings?api-version={api_version}"
    )


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts.

    Uses Azure OpenAI text-embedding-3-small.
    Batches automatically if > 16 texts (recommended limit).
    """
    if not texts:
        return []

    url = _build_url()
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.azure_embedding_api_key,
    }

    all_embeddings: list[list[float]] = []
    batch_size = 16  # Azure recommended batch size

    async with httpx.AsyncClient(timeout=60) as client:
        for i in range(0, len(texts), batch_size):
            batch = list(texts[i : i + batch_size])
            body = {
                "input": batch,
                "dimensions": settings.embedding_dimension,
            }

            resp = await client.post(url, headers=headers, json=body)

            if resp.status_code != 200:
                logger.error("Azure embedding error (%s): %s", resp.status_code, resp.text[:500])
                raise RuntimeError(f"Azure embedding API error: {resp.status_code}")

            data = resp.json()
            # Sort by index to preserve order
            sorted_items = sorted(data["data"], key=lambda x: x["index"])
            all_embeddings.extend([item["embedding"] for item in sorted_items])

    logger.info("Generated %d embeddings (%d-dim)", len(all_embeddings), settings.embedding_dimension)
    return all_embeddings


async def embed_query(text: str) -> list[float]:
    """Generate embedding for a single query text."""
    results = await embed_texts([text])
    return results[0]
