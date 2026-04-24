"""
ConnectedAccount model — stores OAuth tokens encrypted with AES-256-GCM.
Raw tokens are NEVER stored. Only the encrypted form hits the DB.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    provider: Mapped[str] = mapped_column(
        Enum("gmail", "outlook", name="email_provider"), nullable=False
    )
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # AES-256-GCM encrypted OAuth tokens — decrypted in-memory only
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Gmail-specific webhook state
    gmail_history_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gmail_watch_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Outlook-specific webhook state
    outlook_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outlook_subscription_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
