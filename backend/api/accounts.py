"""
Accounts API — list and manage connected email accounts.
All endpoints require a valid JWT (Bearer token).
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from connectors.gmail import GmailConnector
from connectors.outlook import OutlookConnector
from db.session import get_db
from models.account import ConnectedAccount
from models.user import User
from tasks.celery_app import _process_gmail_webhook_async, _process_outlook_webhook_async

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


class AccountOut(BaseModel):
    id: str
    provider: str
    email_address: str
    is_active: bool
    token_expires_at: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all connected email accounts for the logged-in user."""
    result = await db.execute(
        select(ConnectedAccount).where(ConnectedAccount.user_id == current_user.id)
    )
    accounts = result.scalars().all()
    return [
        AccountOut(
            id=str(a.id),
            provider=a.provider,
            email_address=a.email_address,
            is_active=a.is_active,
            token_expires_at=a.token_expires_at.isoformat() if a.token_expires_at else None,
        )
        for a in accounts
    ]


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a connected account (user must own it)."""
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.id == account_id,
            ConnectedAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    await db.delete(account)
    await db.commit()


@router.post("/{account_id}/sync")
async def sync_account_now(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually queue recent inbox messages for processing."""
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.id == account_id,
            ConnectedAccount.user_id == current_user.id,
            ConnectedAccount.is_active == True,  # noqa: E712
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    try:
        if account.provider == "gmail":
            message_ids = GmailConnector(account).list_recent_message_ids(limit=10)
            for mid in message_ids:
                await _process_gmail_webhook_async(str(account.id), mid)
        elif account.provider == "outlook":
            connector = OutlookConnector(account)
            message_ids = await connector.list_recent_message_ids(limit=10)
            # Commit any token refresh that may have occurred
            db.add(account)
            await db.commit()
            for mid in message_ids:
                await _process_outlook_webhook_async(str(account.id), mid)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to enqueue sync: {exc}",
        )

    return {"ok": True, "queued": len(message_ids)}
