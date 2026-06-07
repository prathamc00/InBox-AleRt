"""
FastAPI application entry point.
Includes: security headers, CORS, rate limiting, session middleware, and all routers.
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from auth.google import router as google_router
from auth.microsoft import router as microsoft_router
from api.webhooks import router as webhooks_router
from api.auth import router as auth_router
from api.emails import router as emails_router
from whatsapp.meta_webhook import router as whatsapp_meta_router
from core.config import settings

log = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


async def _keepalive_ping():
    """
    Self-ping loop: hits /health every 10 minutes to prevent Render free tier
    from spinning down the server.

    Render spins down a free web service after 15 minutes of *inbound* silence.
    When the server sleeps the polling loop also dies, so no emails are processed
    and no WhatsApp alerts are sent — even if a new email arrives.

    By pinging ourselves every 10 minutes we stay awake 24/7 at zero extra cost.
    """
    import asyncio
    import httpx

    # Wait for the server to fully start before pinging
    await asyncio.sleep(30)

    # Determine the URL to ping: use the Render public URL if available,
    # otherwise fall back to localhost (works in dev too, just a no-op).
    ping_url = settings.SELF_PING_URL.strip() if settings.SELF_PING_URL.strip() else "http://localhost:8000/health"

    log.info("Keepalive ping started", url=ping_url)

    while True:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(ping_url)
            log.info("Keepalive ping OK", status=resp.status_code, url=ping_url)
        except Exception as exc:
            log.warning("Keepalive ping failed", error=str(exc), url=ping_url)

        # Ping every 10 minutes (Render sleeps after 15 min inactivity)
        await asyncio.sleep(600)


async def _renew_gmail_watches():
    """
    Gmail watch renewal loop: renews all Gmail push-notification subscriptions
    every 6 days.

    Google expires Gmail watches after exactly 7 days. If not renewed, Pub/Sub
    stops sending push notifications and email processing halts silently.
    """
    import asyncio
    from db.session import AsyncSessionLocal
    from models.account import ConnectedAccount
    from connectors.gmail import GmailConnector
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta

    # Wait a bit so server is fully up before doing DB work
    await asyncio.sleep(60)

    SIX_DAYS = 6 * 24 * 3600

    while True:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ConnectedAccount).where(
                        ConnectedAccount.provider == "gmail",
                        ConnectedAccount.is_active == True,
                    )
                )
                accounts = result.scalars().all()
                now = datetime.now(timezone.utc)

                for account in accounts:
                    try:
                        # Renew if expiry is within 24 hours OR watch_expiry is not set
                        needs_renewal = (
                            account.gmail_watch_expiry is None
                            or account.gmail_watch_expiry <= now + timedelta(hours=24)
                        )
                        if needs_renewal:
                            watch_result = GmailConnector(account).watch()
                            history_id = watch_result.get("historyId")
                            watch_expiry_ms = watch_result.get("expiration")
                            if history_id:
                                account.gmail_history_id = str(history_id)
                            if watch_expiry_ms:
                                account.gmail_watch_expiry = datetime.fromtimestamp(
                                    int(watch_expiry_ms) / 1000, tz=timezone.utc
                                )
                            db.add(account)
                            await db.commit()
                            log.info(
                                "Gmail watch renewed",
                                account_id=str(account.id),
                                expires=account.gmail_watch_expiry,
                            )
                    except Exception as exc:
                        log.warning(
                            "Gmail watch renewal failed",
                            account_id=str(account.id),
                            error=str(exc),
                        )
        except Exception as exc:
            log.error("Gmail watch renewal loop error", error=str(exc))

        # Check again in 6 hours — cheap and ensures we never miss the window
        await asyncio.sleep(6 * 3600)


async def _poll_all_accounts():
    """
    Background task: poll all active email accounts every 60s.

    This acts as a fallback for when Gmail/Outlook push webhooks are not firing
    (e.g., shortly after server restart, or if watch has just expired).
    Duplicate processing is prevented by per-account provider_message_id deduplication.
    """
    import asyncio
    from db.session import AsyncSessionLocal
    from models.account import ConnectedAccount
    from connectors.gmail import GmailConnector
    from connectors.outlook import OutlookConnector
    from tasks.celery_app import _process_gmail_webhook_async, _process_outlook_webhook_async
    from sqlalchemy import select

    # Track the most recently seen message IDs per account so we only process
    # genuinely new messages each cycle instead of re-fetching the same 10.
    _seen_ids: dict[str, set[str]] = {}

    while True:
        await asyncio.sleep(60)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ConnectedAccount).where(ConnectedAccount.is_active == True)
                )
                accounts = result.scalars().all()
                for account in accounts:
                    acct_key = str(account.id)
                    if acct_key not in _seen_ids:
                        _seen_ids[acct_key] = set()

                    try:
                        if account.provider == "gmail":
                            ids = GmailConnector(account).list_recent_message_ids(limit=10)
                            new_ids = [mid for mid in ids if mid not in _seen_ids[acct_key]]
                            _seen_ids[acct_key].update(ids)
                            # Keep only last 50 to bound memory usage
                            if len(_seen_ids[acct_key]) > 50:
                                _seen_ids[acct_key] = set(list(_seen_ids[acct_key])[-50:])
                            for mid in new_ids:
                                await _process_gmail_webhook_async(str(account.id), mid)

                        elif account.provider == "outlook":
                            connector = OutlookConnector(account)
                            ids = await connector.list_recent_message_ids(limit=10)
                            new_ids = [mid for mid in ids if mid not in _seen_ids[acct_key]]
                            _seen_ids[acct_key].update(ids)
                            if len(_seen_ids[acct_key]) > 50:
                                _seen_ids[acct_key] = set(list(_seen_ids[acct_key])[-50:])
                            db.add(account)
                            await db.commit()
                            for mid in new_ids:
                                await _process_outlook_webhook_async(str(account.id), mid)

                    except Exception as e:
                        log.warning("Poll failed for account", account_id=acct_key, error=str(e))
        except Exception as e:
            log.error("Polling loop error", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    log.info("InboxAlert API starting", debug=settings.DEBUG)

    # Start all three background tasks in parallel:
    # 1. Self-ping keepalive — prevents Render from sleeping the server
    # 2. Gmail watch renewal — prevents push notifications from expiring after 7 days
    # 3. Email polling — fallback processing loop every 60 seconds
    keepalive_task = asyncio.create_task(_keepalive_ping())
    watch_renewal_task = asyncio.create_task(_renew_gmail_watches())
    poll_task = asyncio.create_task(_poll_all_accounts())

    yield

    poll_task.cancel()
    watch_renewal_task.cancel()
    keepalive_task.cancel()
    log.info("InboxAlert API shutting down")


app = FastAPI(
    title="InboxAlert API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,   # Disable Swagger in prod
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Session (for OAuth state) ─────────────────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.TOKEN_ENCRYPTION_KEY,
    session_cookie="inboxalert_session",
    same_site="lax",
    https_only=not settings.DEBUG,
    max_age=600,  # 10 minutes — only used during OAuth flow
)

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = (
    [settings.FRONTEND_URL]
    if not settings.DEBUG
    else [settings.FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$" if settings.DEBUG else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security Headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not settings.DEBUG:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    return response


# ── Global Exception Handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    log.error("Unhandled exception", path=request.url.path, error=str(exc), traceback=tb)
    if settings.DEBUG:
        # In development, expose full error for easier debugging
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc), "type": type(exc).__name__},
        )
    # In production, return a safe generic message — full details are in server logs
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please try again later."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(google_router)
app.include_router(microsoft_router)
app.include_router(webhooks_router)
app.include_router(emails_router)
app.include_router(whatsapp_meta_router)
from api.billing import router as billing_router
app.include_router(billing_router)
app.include_router(auth_router)
if settings.DEBUG:
    from api.mock_auth import router as mock_auth_router

    app.include_router(mock_auth_router, prefix="/api/v1/auth")
from api.accounts import router as accounts_router
app.include_router(accounts_router)
from api.settings import router as settings_router
app.include_router(settings_router)
from api.auto_reply import router as auto_reply_router
app.include_router(auto_reply_router)

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/debug/gmail-watch", tags=["debug"])
async def debug_gmail_watch(db=None):
    """Manually trigger Gmail watch and return result — DEBUG only."""
    if not settings.DEBUG:
        return {"error": "not available in production"}
    from db.session import AsyncSessionLocal
    from models.account import ConnectedAccount
    from connectors.gmail import GmailConnector
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ConnectedAccount).where(ConnectedAccount.provider == "gmail").limit(1)
        )
        account = result.scalar_one_or_none()
        if not account:
            return {"error": "No Gmail account found"}
        try:
            watch_result = GmailConnector(account).watch()
            account.gmail_history_id = str(watch_result.get("historyId", ""))
            await session.commit()
            return {"ok": True, "watch_result": watch_result}
        except Exception as e:
            return {"ok": False, "error": str(e)}


@app.get("/debug/outlook-test", tags=["debug"])
async def debug_outlook_test():
    """Test Outlook configuration and connectivity — DEBUG only."""
    if not settings.DEBUG:
        return {"error": "not available in production"}
    from db.session import AsyncSessionLocal
    from models.account import ConnectedAccount
    from connectors.outlook import OutlookConnector
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ConnectedAccount).where(ConnectedAccount.provider == "outlook").limit(1)
        )
        account = result.scalar_one_or_none()
        if not account:
            return {"error": "No Outlook account found", "hint": "Try logging in with Microsoft first"}
        
        try:
            connector = OutlookConnector(account, session)
            message_ids = await connector.list_recent_message_ids(limit=5)
            return {
                "ok": True,
                "account_email": account.email_address,
                "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
                "subscription_id": account.outlook_subscription_id,
                "message_count": len(message_ids),
                "message_ids": message_ids[:3]
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "error_type": type(e).__name__}
