"""Qdrant vector store operations — collection management, upsert, search."""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings

logger = logging.getLogger("rag.vector_store")

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        logger.info("Connected to Qdrant at %s:%s", settings.qdrant_host, settings.qdrant_port)
    return _client


def _collection_name(agent_id: str) -> str:
    return f"agent_{agent_id}"


async def ensure_collection(agent_id: str) -> None:
    """Create collection for agent if it doesn't exist."""
    client = _get_client()
    collection_name = _collection_name(agent_id)

    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if collection_name not in existing_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection: %s", collection_name)


async def upsert_vectors(
    agent_id: str,
    points: list[dict[str, Any]],
) -> int:
    """Upsert points into agent's collection.

    Each point dict should have: id, vector, payload.
    """
    client = _get_client()
    collection_name = _collection_name(agent_id)

    await ensure_collection(agent_id)

    qdrant_points = [
        PointStruct(
            id=p["id"],
            vector=p["vector"],
            payload=p["payload"],
        )
        for p in points
    ]

    # Batch upsert (Qdrant handles large batches well)
    batch_size = 100
    total = 0
    for i in range(0, len(qdrant_points), batch_size):
        batch = qdrant_points[i : i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        total += len(batch)

    logger.info("Upserted %d vectors into %s", total, collection_name)
    return total


async def search_vectors(
    agent_id: str,
    query_vector: list[float],
    top_k: int = 5,
    document_id: str | None = None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    """Search agent's collection for similar vectors.

    Returns list of dicts with: id, score, payload.
    """
    client = _get_client()
    collection_name = _collection_name(agent_id)

    # Build filter
    must_conditions = []
    if document_id:
        must_conditions.append(
            FieldCondition(key="document_id", match=MatchValue(value=document_id))
        )
    if domain:
        must_conditions.append(
            FieldCondition(key="domain", match=MatchValue(value=domain))
        )

    search_filter = Filter(must=must_conditions) if must_conditions else None

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
        query_filter=search_filter,
        with_payload=True,
    )

    return [
        {
            "id": str(point.id),
            "score": point.score,
            "payload": point.payload,
        }
        for point in results.points
    ]


async def delete_by_document(agent_id: str, document_id: str) -> None:
    """Delete all vectors belonging to a specific document."""
    client = _get_client()
    collection_name = _collection_name(agent_id)

    client.delete(
        collection_name=collection_name,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )
    logger.info("Deleted vectors for document %s from %s", document_id, collection_name)


async def delete_collection(agent_id: str) -> None:
    """Delete the entire Qdrant collection for an agent."""
    client = _get_client()
    collection_name = _collection_name(agent_id)

    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if collection_name in existing_names:
        client.delete_collection(collection_name=collection_name)
        logger.info("Deleted Qdrant collection: %s", collection_name)
