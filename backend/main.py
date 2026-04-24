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
from whatsapp.reply_handler import router as whatsapp_router
from whatsapp.meta_webhook import router as whatsapp_meta_router
from core.config import settings

log = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address)


async def _poll_all_accounts():
    """Background task: poll all active Gmail accounts every 60s."""
    import asyncio
    from db.session import AsyncSessionLocal
    from models.account import ConnectedAccount
    from connectors.gmail import GmailConnector
    from tasks.celery_app import _process_gmail_webhook_async
    from sqlalchemy import select

    while True:
        await asyncio.sleep(60)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ConnectedAccount).where(
                        ConnectedAccount.is_active == True,
                        ConnectedAccount.provider == "gmail",
                    )
                )
                accounts = result.scalars().all()
                for account in accounts:
                    try:
                        ids = GmailConnector(account).list_recent_message_ids(limit=5)
                        for mid in ids:
                            await _process_gmail_webhook_async(str(account.id), mid)
                    except Exception as e:
                        log.warning("Poll failed for account", account_id=str(account.id), error=str(e))
        except Exception as e:
            log.error("Polling loop error", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    log.info("InboxAlert API starting", debug=settings.DEBUG)
    if settings.DEBUG:
        task = asyncio.create_task(_poll_all_accounts())
    yield
    if settings.DEBUG:
        task.cancel()
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
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
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
    log.error("Unhandled exception", path=request.url.path, error=str(exc))
    # Never leak stack traces to the frontend in production.
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(google_router)
app.include_router(microsoft_router)
app.include_router(webhooks_router)
app.include_router(emails_router)
app.include_router(whatsapp_router)
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
