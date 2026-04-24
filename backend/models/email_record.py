"""
EmailRecord model — stores metadata only.
Raw email body is NEVER persisted. Processed in-memory and discarded.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class EmailRecord(Base):
    __tablename__ = "email_records"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "provider_message_id",
            name="uq_email_records_account_provider_message",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("connected_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Email identifiers (from provider)
    provider_message_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    provider_thread_id: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Metadata (safe to store — no body content)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)  # RFC 2822 limit
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # AI-generated summary (safe to store — no raw body)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100

    # State
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | alerted | auto_replied | manual_replied | snoozed | ignored

    # Auto-reply tracking
    auto_replied: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_reply_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_reply_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # User feedback for AI learning
    user_feedback: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # important | not_important

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
