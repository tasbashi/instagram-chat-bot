"""Sliding-window text chunker with sentence-boundary awareness."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class TextChunk:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    source: str = ""
    section_title: str = ""
    page_number: int = 0
    chunk_index: int = 0
    token_count: int = 0


# Simple sentence splitter — handles ., !, ? followed by whitespace
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 4 characters."""
    return len(text) // 4


def chunk_text(
    text: str,
    source: str = "",
    section_title: str = "",
    page_number: int = 0,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[TextChunk]:
    """Split text into overlapping chunks respecting sentence boundaries.

    Args:
        text: Raw text to chunk.
        source: Source identifier (e.g. filename).
        section_title: Section heading the text belongs to.
        page_number: Page number in source document.
        chunk_size: Target chunk size in tokens. Defaults to settings.
        chunk_overlap: Overlap between chunks in tokens. Defaults to settings.

    Returns:
        List of TextChunk objects.
    """
    if not text or not text.strip():
        return []

    chunk_size = chunk_size or settings.chunk_size_tokens
    chunk_overlap = chunk_overlap or settings.chunk_overlap_tokens

    sentences = _SENTENCE_RE.split(text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[TextChunk] = []
    current_sentences: list[str] = []
    current_tokens = 0
    chunk_index = 0

    for sentence in sentences:
        sentence_tokens = _estimate_tokens(sentence)

        if current_tokens + sentence_tokens > chunk_size and current_sentences:
            # Emit chunk
            chunk_text_str = " ".join(current_sentences)
            chunks.append(TextChunk(
                text=chunk_text_str,
                source=source,
                section_title=section_title,
                page_number=page_number,
                chunk_index=chunk_index,
                token_count=current_tokens,
            ))
            chunk_index += 1

            # Compute overlap: keep last N sentences that fit within overlap budget
            overlap_sentences: list[str] = []
            overlap_tokens = 0
            for s in reversed(current_sentences):
                s_tokens = _estimate_tokens(s)
                if overlap_tokens + s_tokens > chunk_overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_tokens += s_tokens

            current_sentences = overlap_sentences
            current_tokens = overlap_tokens

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Final chunk
    if current_sentences:
        chunk_text_str = " ".join(current_sentences)
        chunks.append(TextChunk(
            text=chunk_text_str,
            source=source,
            section_title=section_title,
            page_number=page_number,
            chunk_index=chunk_index,
            token_count=current_tokens,
        ))

    return chunks
