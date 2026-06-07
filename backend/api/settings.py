"""
Settings API — GET/PATCH user notification preferences & WhatsApp number.
Preferences are stored directly on the User model.
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import get_db
from models.user import User
from whatsapp.meta_notifier import meta_notifier as notifier
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
limiter = Limiter(key_func=get_remote_address)


# ── Schemas ────────────────────────────────────────────────────────────────────

class SettingsOut(BaseModel):
    whatsapp_number: str | None
    whatsapp_verified: bool
    notify_on_all: bool
    notify_daily_digest: bool

    model_config = {"from_attributes": True}


class SettingsPatch(BaseModel):
    whatsapp_number: str | None = Field(None, max_length=20)
    notify_on_all: bool | None = None
    notify_daily_digest: bool | None = None


class WhatsAppDeliveryItem(BaseModel):
    sid: str | None
    to: str | None
    from_number: str | None
    status: str | None
    error_code: int | None
    error_message: str | None
    date_sent: str | None


class WhatsAppDeliveriesOut(BaseModel):
    items: list[WhatsAppDeliveryItem]


def _normalize_whatsapp_number(raw: str) -> str:
    number = re.sub(r"\s+", "", raw.strip())
    if not number:
        return ""
    if not number.startswith("+"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="WhatsApp number must start with '+' and include country code.",
        )
    if not re.fullmatch(r"\+[1-9]\d{7,14}", number):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid WhatsApp number format.",
        )
    return number


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", response_model=SettingsOut)
async def get_settings(
    current_user: User = Depends(get_current_user),
):
    """Return the current user's notification preferences."""
    return SettingsOut(
        whatsapp_number=current_user.whatsapp_number,
        whatsapp_verified=current_user.whatsapp_verified,
        notify_on_all=current_user.notify_on_all,
        notify_daily_digest=current_user.notify_daily_digest,
    )


@router.patch("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsPatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partially update the current user's notification preferences."""
    changed = False

    if payload.whatsapp_number is not None:
        number = _normalize_whatsapp_number(payload.whatsapp_number)
        if current_user.whatsapp_number != number:
            current_user.whatsapp_number = number
            # If the number changed, reset verification
            current_user.whatsapp_verified = False
            changed = True

    if payload.notify_on_all is not None:
        current_user.notify_on_all = payload.notify_on_all
        changed = True

    if payload.notify_daily_digest is not None:
        current_user.notify_daily_digest = payload.notify_daily_digest
        changed = True

    if changed:
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)

    return SettingsOut(
        whatsapp_number=current_user.whatsapp_number,
        whatsapp_verified=current_user.whatsapp_verified,
        notify_on_all=current_user.notify_on_all,
        notify_daily_digest=current_user.notify_daily_digest,
    )


@router.post("/whatsapp/test")
@limiter.limit("3/hour")
async def send_whatsapp_test(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test WhatsApp message to the saved number and mark it verified on success.
    Rate-limited to 3 requests per hour per IP to prevent WhatsApp number abuse.
    """
    if not current_user.whatsapp_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add your WhatsApp number in settings first.",
        )

    try:
        ok, detail = notifier.send_test_message_result(current_user.whatsapp_number)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WhatsApp provider error: {exc}",
        ) from exc

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not send WhatsApp test message. {detail}",
        )

    if not current_user.whatsapp_verified:
        current_user.whatsapp_verified = True
        db.add(current_user)
        await db.commit()

    return {"ok": True, "detail": "Test message sent to WhatsApp."}


@router.get("/whatsapp/diagnostics")
async def get_whatsapp_diagnostics(
    current_user: User = Depends(get_current_user),
):
    """Return non-secret provider diagnostics for WhatsApp sends."""
    return {
        "configured_number": current_user.whatsapp_number,
        "is_verified": current_user.whatsapp_verified,
        "provider": notifier.diagnostics(),
    }


@router.get("/whatsapp/deliveries", response_model=WhatsAppDeliveriesOut)
async def get_whatsapp_deliveries(
    current_user: User = Depends(get_current_user),
):
    """Return recent WhatsApp delivery statuses for the current user's WhatsApp number."""
    if not current_user.whatsapp_number:
        return WhatsAppDeliveriesOut(items=[])

    # Meta API doesn't have a delivery list endpoint — return empty for now
    return WhatsAppDeliveriesOut(items=[])
