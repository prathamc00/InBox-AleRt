"""
User model — every record is scoped to a tenant.
Role: owner | admin | member | viewer
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Role-Based Access Control
    role: Mapped[str] = mapped_column(
        Enum("owner", "admin", "member", "viewer", name="user_role"),
        nullable=False,
        default="owner",
    )

    # WhatsApp notification target
    whatsapp_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notification preferences
    notify_on_all: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_daily_digest: Mapped[bool] = mapped_column(Boolean, default=True)

    # Account state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Billing
    tier: Mapped[str] = mapped_column(String(50), default="free")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
