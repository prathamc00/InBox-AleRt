"""
Google OAuth 2.0.
Flow: /auth/google/login → Google → /auth/google/callback → redirect to frontend with JWT
"""
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.gmail import GmailConnector
from core.config import settings
from core.security import (
    create_access_token,
    create_refresh_token,
    encrypt_token,
    generate_oauth_state,
)
from db.session import get_db
from models.account import ConnectedAccount
from models.auto_reply import AutoReplyRule
from models.refresh_token import RefreshToken
from models.user import User

router = APIRouter(prefix="/auth/google", tags=["auth"])
log = structlog.get_logger()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


@router.get("/login")
async def google_login(request: Request):
    """Redirect user to Google OAuth consent screen."""
    state = generate_oauth_state()
    # Store state in server-side session (Redis-backed in prod)
    request.session["oauth_state"] = state

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",  # always get refresh_token
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback, issue JWT."""
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Google OAuth error: {error}")

    if not code or not state:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing OAuth code/state")

    # Verify CSRF state
    stored_state = request.session.pop("oauth_state", None)
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {token_resp.status_code} {token_resp.text}",
        )

    token_data = token_resp.json()
    access_token_google = token_data["access_token"]
    refresh_token_google = token_data.get("refresh_token", "")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token_google}"},
        )
    if user_resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch user info")

    info = user_resp.json()
    email = info["email"]
    display_name = info.get("name", email)
    avatar_url = info.get("picture")

    # Upsert user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    is_new_user = False
    if not user:
        is_new_user = True
        tenant_id = uuid.uuid4()
        user = User(
            tenant_id=tenant_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            role="owner",
            email_verified=True,
        )
        db.add(user)
        await db.flush()

        # Create default auto-reply rule (dry-run ON by default)
        auto_reply = AutoReplyRule(
            tenant_id=user.tenant_id,
            user_id=user.id,
            is_enabled=False,
            dry_run=True,
        )
        db.add(auto_reply)
    else:
        user.last_login_at = datetime.now(timezone.utc)
        user.avatar_url = avatar_url

    # Upsert connected account with encrypted tokens
    acc_result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.provider == "gmail",
            ConnectedAccount.email_address == email,
        )
    )
    account = acc_result.scalar_one_or_none()
    expires_in = token_data.get("expires_in", 3600)

    if not account:
        account = ConnectedAccount(
            tenant_id=user.tenant_id,
            user_id=user.id,
            provider="gmail",
            email_address=email,
            encrypted_access_token=encrypt_token(access_token_google),
            encrypted_refresh_token=encrypt_token(refresh_token_google) if refresh_token_google else "",
            token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        )
        db.add(account)
    else:
        account.encrypted_access_token = encrypt_token(access_token_google)
        if refresh_token_google:
            account.encrypted_refresh_token = encrypt_token(refresh_token_google)
        account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Ensure Gmail push notifications are active for AI ingestion.
    try:
        watch_result = GmailConnector(account).watch()
        history_id = watch_result.get("historyId")
        if history_id:
            account.gmail_history_id = str(history_id)

        watch_expiry = watch_result.get("expiration")
        if watch_expiry:
            account.gmail_watch_expiry = datetime.fromtimestamp(
                int(watch_expiry) / 1000,
                tz=timezone.utc,
            )
    except Exception as exc:
        # Do not block OAuth login if watch activation fails.
        log.warning("Gmail watch setup failed", email=email, error=str(exc))

    # Issue our JWT + refresh token
    raw_refresh, hashed_refresh = create_refresh_token()
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_record)
    await db.commit()

    access_jwt = create_access_token(
        str(user.id), str(user.tenant_id), user.role
    )

    # Redirect to frontend callback page with tokens in query string
    frontend_url = settings.FRONTEND_URL
    params = urlencode({
        "access_token": access_jwt,
        "refresh_token": raw_refresh,
        "is_new_user": str(is_new_user).lower(),
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url or "",
        "role": user.role,
    })
    return RedirectResponse(url=f"{frontend_url}/callback?{params}")
