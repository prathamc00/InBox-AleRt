"""
AutoReplyRule model — governs when and how the AI auto-replies.
Granular controls: global toggle, scope, limits, dry-run mode, hours.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AutoReplyRule(Base):
    __tablename__ = "auto_reply_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # ── Core Toggle ─────────────────────────────────────────
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Dry-Run Mode (default ON for new users — AI drafts but does NOT send) ──
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Scope ───────────────────────────────────────────────
    # If set, only auto-reply to emails from these domains (comma-separated)
    allowed_sender_domains: Mapped[str | None] = mapped_column(Text, nullable=True)
    # If set, only auto-reply to emails from these addresses (comma-separated)
    allowed_sender_emails: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Score Threshold ─────────────────────────────────────
    # Only auto-reply if importance score >= this value (default 90)
    min_importance_score: Mapped[int] = mapped_column(Integer, default=90)

    # ── Tone ────────────────────────────────────────────────
    reply_tone: Mapped[str] = mapped_column(
        String(20), default="professional"
    )  # professional | friendly | brief

    # ── Limits & Safety ─────────────────────────────────────
    daily_auto_reply_limit: Mapped[int] = mapped_column(Integer, default=50)
    # Per-thread loop protection: pause after N auto-replies to same thread
    max_replies_per_thread: Mapped[int] = mapped_column(Integer, default=3)

    # ── Cancellation Window ─────────────────────────────────
    # Seconds to wait before actually sending (user can cancel via WhatsApp)
    cancel_window_seconds: Mapped[int] = mapped_column(Integer, default=60)

    # ── Business Hours ──────────────────────────────────────
    business_hours_only: Mapped[bool] = mapped_column(Boolean, default=False)
    business_hours_start: Mapped[str] = mapped_column(String(5), default="09:00")  # HH:MM
    business_hours_end: Mapped[str] = mapped_column(String(5), default="18:00")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
