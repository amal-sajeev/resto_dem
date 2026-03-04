"""
AES-256-GCM encryption utilities for PII protection.
Encrypted values are stored as base64(nonce || ciphertext || tag).
Phone numbers also get an HMAC-SHA256 blind index for DB lookups.
"""

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

_NONCE_SIZE = 12  # 96-bit nonce recommended for AES-GCM


def _get_key() -> bytes:
    return bytes.fromhex(settings.AES_ENCRYPTION_KEY)


def encrypt(plaintext: str) -> str:
    key = _get_key()
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt(token: str) -> str:
    key = _get_key()
    raw = base64.b64decode(token)
    nonce, ct = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")


def phone_hash(phone: str) -> str:
    """HMAC-SHA256 blind index so we can look up users by phone without decrypting."""
    key = _get_key()
    return hmac.new(key, phone.encode("utf-8"), hashlib.sha256).hexdigest()
