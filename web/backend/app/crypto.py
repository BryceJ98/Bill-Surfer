"""
crypto.py — AES-256 encryption for user API keys using Fernet (AES-128-CBC + HMAC-SHA256).
Keys are never stored in plaintext. The encryption secret lives only in the
server environment and is never sent to the client or stored in the database.

Generate a secret with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import os
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        secret = os.getenv("KEY_ENCRYPTION_SECRET")
        if not secret:
            raise RuntimeError("KEY_ENCRYPTION_SECRET environment variable is not set")
        _fernet = Fernet(secret.encode())
    return _fernet


def encrypt_key(plaintext: str) -> str:
    """Encrypt an API key string. Returns a base64 ciphertext string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """Decrypt a stored ciphertext back to the plaintext API key."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key — encryption secret may have changed",
        )
