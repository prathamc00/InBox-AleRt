"""
Auto-Reply Rules API — GET and PUT the user's autonomous reply configuration.
One rule per user (upsert pattern).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from auth.dependencies import get_current_user
from db.session import get_db
from models.auto_reply import AutoReplyRule
from models.user import User

router = APIRouter(prefix="/api/v1/auto-reply", tags=["auto-reply"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class AutoReplyOut(BaseModel):
    is_enabled: bool
    dry_run: bool
    min_importance_score: int
    reply_tone: str
    daily_auto_reply_limit: int
    cancel_window_seconds: int
    business_hours_only: bool
    business_hours_start: str
    business_hours_end: str
    timezone: str

    model_config = {"from_attributes": True}


class AutoReplyPut(BaseModel):
    is_enabled: bool
    dry_run: bool
    min_importance_score: int = Field(ge=80, le=99)
    reply_tone: str = Field(pattern="^(professional|friendly|brief)$")
    daily_auto_reply_limit: int = Field(ge=5, le=100)
    cancel_window_seconds: int = Field(ge=15, le=300)
    business_hours_only: bool
    business_hours_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    business_hours_end: str = Field(default="18:00", pattern=r"^\d{2}:\d{2}$")
    timezone: str = Field(default="UTC", max_length=50)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_or_create_rule(user: User, db: AsyncSession) -> AutoReplyRule:
    """Fetch or create a default AutoReplyRule for the user."""
    result = await db.execute(
        select(AutoReplyRule).where(AutoReplyRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        rule = AutoReplyRule(
            id=uuid.uuid4(),
            tenant_id=user.tenant_id,
            user_id=user.id,
        )
        db.add(rule)
        await db.flush()
    return rule


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", response_model=AutoReplyOut)
async def get_auto_reply_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's auto-reply rule (creates defaults if none)."""
    rule = await _get_or_create_rule(current_user, db)
    await db.commit()
    return AutoReplyOut.model_validate(rule)


@router.put("", response_model=AutoReplyOut)
async def update_auto_reply_config(
    payload: AutoReplyPut,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fully replace (upsert) the current user's auto-reply rule."""
    rule = await _get_or_create_rule(current_user, db)

    rule.is_enabled = payload.is_enabled
    rule.dry_run = payload.dry_run
    rule.min_importance_score = payload.min_importance_score
    rule.reply_tone = payload.reply_tone
    rule.daily_auto_reply_limit = payload.daily_auto_reply_limit
    rule.cancel_window_seconds = payload.cancel_window_seconds
    rule.business_hours_only = payload.business_hours_only
    rule.business_hours_start = payload.business_hours_start
    rule.business_hours_end = payload.business_hours_end
    rule.timezone = payload.timezone

    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return AutoReplyOut.model_validate(rule)
