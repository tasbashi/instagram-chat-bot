"""Full RAG ingestion pipeline: PDF → parse → chunk → embed → store in Qdrant."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.services.rag.pdf_parser import parse_pdf
from app.services.rag.chunker import chunk_text
from app.services.rag.embedder import embed_texts
from app.services.rag.vector_store import ensure_collection, upsert_vectors

logger = logging.getLogger("rag.ingestion")


async def ingest_pdf(
    pdf_path: str,
    agent_id: str,
    document_id: str,
) -> dict[str, Any]:
    """End-to-end PDF ingestion.

    1. Parse PDF → extract text + sections
    2. Chunk sections into overlapping text chunks
    3. Generate embeddings via Vertex AI
    4. Upsert into Qdrant (agent-scoped collection)

    Returns ingestion trace with stats.
    """
    start = time.time()

    # ── Step 1: Parse ──
    logger.info("Parsing PDF: %s", pdf_path)
    pdf_result = parse_pdf(pdf_path)

    # ── Step 2: Chunk ──
    all_chunks = []
    for section in pdf_result.sections:
        section_chunks = chunk_text(
            text=section.content,
            source=pdf_path,
            section_title=section.title,
            page_number=section.page_number,
        )
        all_chunks.extend(section_chunks)

    # Fallback: if no sections detected, chunk the full text
    if not all_chunks:
        all_chunks = chunk_text(
            text=pdf_result.text,
            source=pdf_path,
            section_title="Full Document",
            page_number=1,
        )

    if not all_chunks:
        logger.warning("No chunks generated from PDF: %s", pdf_path)
        return {
            "page_count": pdf_result.page_count,
            "chunk_count": 0,
            "embedding_time_ms": 0,
            "total_time_ms": int((time.time() - start) * 1000),
        }

    logger.info("Generated %d chunks from %d sections", len(all_chunks), len(pdf_result.sections))

    # ── Step 3: Embed ──
    embed_start = time.time()
    texts = [chunk.text for chunk in all_chunks]
    embeddings = await embed_texts(texts)
    embed_time_ms = int((time.time() - embed_start) * 1000)

    # ── Step 4: Store in Qdrant ──
    await ensure_collection(agent_id)

    points = [
        {
            "id": chunk.id,
            "vector": embedding,
            "payload": {
                "chunk_text": chunk.text,
                "document_id": document_id,
                "filename": pdf_path.split("/")[-1],
                "section_title": chunk.section_title,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "source": chunk.source,
            },
        }
        for chunk, embedding in zip(all_chunks, embeddings, strict=True)
    ]

    await upsert_vectors(agent_id, points)

    total_time_ms = int((time.time() - start) * 1000)
    logger.info(
        "Ingestion complete: %d chunks, %dms embedding, %dms total",
        len(all_chunks), embed_time_ms, total_time_ms,
    )

    return {
        "page_count": pdf_result.page_count,
        "chunk_count": len(all_chunks),
        "embedding_time_ms": embed_time_ms,
        "total_time_ms": total_time_ms,
    }
