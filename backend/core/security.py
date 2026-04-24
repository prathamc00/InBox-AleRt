"""
Security utilities:
- AES-256-GCM encryption/decryption (for stored OAuth tokens)
- RS256 JWT creation and verification
- Refresh token generation & hashing
"""
import base64
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── AES-256-GCM ───────────────────────────────────────────────────────────────


def encrypt_token(plaintext: str) -> str:
    """Encrypt an OAuth token with AES-256-GCM. Returns base64url-encoded ciphertext."""
    key = bytes.fromhex(settings.TOKEN_ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit random nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_token(encrypted: str) -> str:
    """Decrypt an AES-256-GCM encrypted token. Raises ValueError on tamper."""
    key = bytes.fromhex(settings.TOKEN_ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    raw = base64.urlsafe_b64decode(encrypted)
    nonce, ciphertext = raw[:12], raw[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


# ── JWT (RS256) ───────────────────────────────────────────────────────────────


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    """Create a short-lived RS256 signed JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "jti": str(uuid.uuid4()),  # unique ID for revocation
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_private_key, algorithm="RS256")


def create_refresh_token() -> tuple[str, str]:
    """
    Generate a cryptographically secure refresh token.
    Returns (raw_token, hashed_token).
    Store only the hash in the database.
    """
    raw = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_access_token(token: str) -> dict:
    """
    Verify and decode a JWT. Raises JWTError on invalid/expired tokens.
    Never catch this broadly — let it propagate to the 401 handler.
    """
    return jwt.decode(
        token,
        settings.jwt_public_key,
        algorithms=["RS256"],
        options={"require": ["exp", "sub", "tenant_id", "jti", "type"]},
    )


# ── OAuth State (PKCE + anti-CSRF) ────────────────────────────────────────────


def generate_oauth_state() -> str:
    """Generate a cryptographically random state param for OAuth flows."""
    return secrets.token_urlsafe(32)
