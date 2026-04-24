import base64
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from connectors.gmail import GmailConnector
from connectors.outlook import OutlookConnector
from core.config import settings
from db.session import get_db
from models.account import ConnectedAccount
from tasks.celery_app import process_gmail_webhook, process_outlook_webhook

log = structlog.get_logger()

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/gmail")
async def gmail_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receive push notifications from Google Cloud Pub/Sub.
    """
    try:
        envelope = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    pubsub_message = envelope.get("message", {})
    data_b64 = pubsub_message.get("data")
    if not data_b64:
        return Response(status_code=204)

    try:
        decoded = base64.b64decode(data_b64).decode("utf-8")
        payload = json.loads(decoded)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed Pub/Sub message data")

    account_email = payload.get("emailAddress")
    latest_history_id = payload.get("historyId")
    direct_message_id = payload.get("messageId")

    if not account_email:
        return Response(status_code=204)

    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.provider == "gmail",
            ConnectedAccount.email_address == account_email,
            ConnectedAccount.is_active == True,  # noqa: E712
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        log.warning("Gmail webhook for unknown account", email=account_email)
        return Response(status_code=202)

    message_ids: list[str] = []
    if direct_message_id:
        message_ids = [direct_message_id]
    elif latest_history_id:
        if account.gmail_history_id:
            try:
                connector = GmailConnector(account)
                message_ids = connector.list_message_ids_since(account.gmail_history_id)
            except Exception as exc:
                log.error(
                    "Failed to fetch Gmail history delta",
                    account_id=str(account.id),
                    error=str(exc),
                )
        account.gmail_history_id = str(latest_history_id)
        db.add(account)
        await db.commit()

    for message_id in message_ids:
        process_gmail_webhook.delay(str(account.id), message_id)

    return Response(status_code=202)

@router.post("/outlook")
async def outlook_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receive push notifications from Microsoft Graph.
    Microsoft sends a validationToken on first subscription, which must be returned.
    """
    if request.query_params.get("validationToken"):
        return Response(content=request.query_params["validationToken"], media_type="text/plain")

    payload = await request.json()

    # Verify the clientState matches what we set during subscription
    if payload.get("value"):
        for notification in payload["value"]:
            if notification.get("clientState") != settings.OUTLOOK_WEBHOOK_CLIENT_STATE:
                raise HTTPException(status_code=403, detail="Invalid clientState")

            subscription_id = notification.get("subscriptionId")
            resource_data = notification.get("resourceData", {}) or {}
            message_id = resource_data.get("id")
            if not message_id or not subscription_id:
                continue

            result = await db.execute(
                select(ConnectedAccount).where(
                    ConnectedAccount.provider == "outlook",
                    ConnectedAccount.outlook_subscription_id == subscription_id,
                    ConnectedAccount.is_active == True,  # noqa: E712
                )
            )
            account = result.scalar_one_or_none()
            if not account:
                log.warning("Outlook webhook for unknown subscription", subscription_id=subscription_id)
                continue

            process_outlook_webhook.delay(str(account.id), message_id)

    return Response(status_code=202)
