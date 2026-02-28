"""Fernet-based encryption for sensitive config values (API keys, secrets).

Uses AES-128-CBC under the hood. Key is sourced from settings.encryption_key.
Idempotent: decrypt() on plaintext returns it unchanged (migration-safe).
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("encryption")

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazy-init the Fernet instance from settings."""
    global _fernet
    if _fernet is None:
        from app.config import settings
        _fernet = Fernet(settings.encryption_key.encode())
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string → URL-safe base64 Fernet token."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token → plaintext string.

    If the value isn't a valid Fernet token (e.g. legacy plaintext),
    returns it unchanged for seamless migration.
    """
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # Not encrypted yet (legacy data) — return as-is
        logger.debug("Value is not a Fernet token — returning as plaintext (migration)")
        return ciphertext


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """Mask a secret for display: 'sk-abc123xyz' → 'sk-a***xyz'."""
    if not value or len(value) <= visible_chars * 2:
        return "••••••••"
    prefix = value[:visible_chars]
    suffix = value[-visible_chars:]
    return f"{prefix}{'•' * 8}{suffix}"
