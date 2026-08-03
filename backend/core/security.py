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

from cryptography.exceptions import InvalidTag
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
    try:
        key = bytes.fromhex(settings.TOKEN_ENCRYPTION_KEY)
        aesgcm = AESGCM(key)
        raw = base64.urlsafe_b64decode(encrypted)
        nonce, ciphertext = raw[:12], raw[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except InvalidTag as e:
        raise ValueError(
            "Failed to decrypt token: Invalid tag (possibly encrypted with a different TOKEN_ENCRYPTION_KEY or tampered)"
        ) from e


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


def generate_oauth_state(user_id: str | None = None, redirect_uri: str | None = None) -> str:
    """
    Generate a cryptographically signed, stateless state parameter for OAuth flows.
    Contains nonce, user_id (if linking), redirect_uri, and expiry (15 mins).
    Signed with HS256 using TOKEN_ENCRYPTION_KEY so it doesn't depend on session cookies.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "nonce": secrets.token_hex(16),
        "user_id": str(user_id) if user_id else None,
        "redirect_uri": redirect_uri,
        "exp": now + timedelta(minutes=15),
        "type": "oauth_state",
    }
    return jwt.encode(payload, settings.TOKEN_ENCRYPTION_KEY, algorithm="HS256")


def decode_oauth_state(state: str) -> dict:
    """
    Decode and verify the OAuth state token.
    Returns the payload dictionary if valid.
    Raises ValueError if invalid, tampered, or expired.
    """
    try:
        payload = jwt.decode(
            state,
            settings.TOKEN_ENCRYPTION_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "type", "nonce"]},
        )
        if payload.get("type") != "oauth_state":
            raise ValueError("Invalid state type")
        return payload
    except Exception as exc:
        raise ValueError(f"Invalid OAuth state: {exc}") from exc

