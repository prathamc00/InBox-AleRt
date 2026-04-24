"""
Microsoft OAuth 2.0 using MSAL.
Flow: /auth/microsoft/login → Microsoft → /auth/microsoft/callback → redirect to frontend with JWT
"""
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import msal
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import (
    create_access_token,
    create_refresh_token,
    encrypt_token,
    generate_oauth_state,
)
from connectors.outlook import OutlookConnector
from db.session import get_db
from models.account import ConnectedAccount
from models.auto_reply import AutoReplyRule
from models.refresh_token import RefreshToken
from models.user import User

router = APIRouter(prefix="/auth/microsoft", tags=["auth"])

SCOPES = [
    "User.Read",
    "Mail.Read",
    "Mail.Send",
]


def _build_msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        settings.MICROSOFT_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}",
        client_credential=settings.MICROSOFT_CLIENT_SECRET,
    )


@router.get("/login")
async def microsoft_login(request: Request):
    """Redirect user to Microsoft OAuth consent screen."""
    state = generate_oauth_state()
    request.session["oauth_state"] = state

    msal_app = _build_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPES,
        state=state,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def microsoft_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Microsoft OAuth callback, issue JWT."""
    stored_state = request.session.pop("oauth_state", None)
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")

    msal_app = _build_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error_description", "Token exchange failed"),
        )

    access_token_ms = result["access_token"]
    refresh_token_ms = result.get("refresh_token", "")
    id_token_claims = result.get("id_token_claims", {})

    email = id_token_claims.get("preferred_username") or id_token_claims.get("email", "")
    display_name = id_token_claims.get("name", email)

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not retrieve email from Microsoft")

    # Upsert user
    db_result = await db.execute(select(User).where(User.email == email))
    user = db_result.scalar_one_or_none()

    is_new_user = False
    if not user:
        is_new_user = True
        tenant_id = uuid.uuid4()
        user = User(
            tenant_id=tenant_id,
            email=email,
            display_name=display_name,
            role="owner",
            email_verified=True,
        )
        db.add(user)
        await db.flush()

        auto_reply = AutoReplyRule(
            tenant_id=user.tenant_id,
            user_id=user.id,
            is_enabled=False,
            dry_run=True,
        )
        db.add(auto_reply)
    else:
        user.last_login_at = datetime.now(timezone.utc)

    # Upsert connected account
    acc_result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.provider == "outlook",
            ConnectedAccount.email_address == email,
        )
    )
    account = acc_result.scalar_one_or_none()
    expires_in = result.get("expires_in", 3600)

    if not account:
        account = ConnectedAccount(
            tenant_id=user.tenant_id,
            user_id=user.id,
            provider="outlook",
            email_address=email,
            encrypted_access_token=encrypt_token(access_token_ms),
            encrypted_refresh_token=encrypt_token(refresh_token_ms) if refresh_token_ms else "",
            token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        )
        db.add(account)
    else:
        account.encrypted_access_token = encrypt_token(access_token_ms)
        if refresh_token_ms:
            account.encrypted_refresh_token = encrypt_token(refresh_token_ms)
        account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    raw_refresh, hashed_refresh = create_refresh_token()
    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_record)
    await db.commit()

    # Register Outlook push notifications for this connected account.
    try:
        webhook_url = str(request.base_url).rstrip("/") + "/api/webhooks/outlook"
        connector = OutlookConnector(account)
        subscription = await connector.create_subscription(webhook_url)
        account.outlook_subscription_id = subscription.get("id")
        expiry = subscription.get("expirationDateTime")
        if expiry:
            try:
                account.outlook_subscription_expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            except Exception:
                account.outlook_subscription_expiry = datetime.now(timezone.utc) + timedelta(days=2)
        db.add(account)
        await db.commit()
    except Exception:
        # Don't block OAuth login if subscription creation fails.
        pass

    access_jwt = create_access_token(str(user.id), str(user.tenant_id), user.role)

    # Redirect to frontend callback page with tokens
    frontend_url = settings.FRONTEND_URL
    params = urlencode({
        "access_token": access_jwt,
        "refresh_token": raw_refresh,
        "is_new_user": str(is_new_user).lower(),
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": "",
        "role": user.role,
    })
    return RedirectResponse(url=f"{frontend_url}/callback?{params}")
