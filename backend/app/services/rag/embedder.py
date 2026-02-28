"""Vertex AI embedding client."""

from __future__ import annotations

import logging
from typing import Sequence

from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

from app.config import settings

logger = logging.getLogger("rag.embedder")

_model: TextEmbeddingModel | None = None


def _get_model() -> TextEmbeddingModel:
    global _model
    if _model is None:
        aiplatform.init(
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )
        _model = TextEmbeddingModel.from_pretrained(settings.embedding_model)
        logger.info("Initialized embedding model: %s", settings.embedding_model)
    return _model


async def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts.

    Uses Vertex AI text-embedding-004 (768 dimensions).
    Batches automatically if > 250 texts (API limit).
    """
    model = _get_model()

    all_embeddings: list[list[float]] = []
    batch_size = 250  # Vertex AI limit

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        inputs = [
            TextEmbeddingInput(text=t, task_type="RETRIEVAL_DOCUMENT")
            for t in batch
        ]
        embeddings = model.get_embeddings(inputs)
        all_embeddings.extend([e.values for e in embeddings])

    logger.info("Generated %d embeddings", len(all_embeddings))
    return all_embeddings


async def embed_query(text: str) -> list[float]:
    """Generate embedding for a single query text."""
    model = _get_model()
    inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_QUERY")]
    embeddings = model.get_embeddings(inputs)
    return embeddings[0].values
