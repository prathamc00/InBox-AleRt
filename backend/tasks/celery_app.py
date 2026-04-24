import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from celery import Celery
import structlog
from sqlalchemy import select

from core.config import settings
from db.session import AsyncSessionLocal
from models.account import ConnectedAccount
from models.auto_reply import AutoReplyRule
from models.email_record import EmailRecord
from models.user import User
from connectors.gmail import GmailConnector
from connectors.outlook import OutlookConnector
from engine.scorer import process_incoming_email
from whatsapp.notifier import notifier

log = structlog.get_logger()

celery_app = Celery(
    "inboxalert_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

async def _process_gmail_webhook_async(account_id: str, message_id: str):
    """Async implementation of the task."""
    async with AsyncSessionLocal() as db:
        account = await db.get(ConnectedAccount, account_id)
        if not account:
            log.error("Account not found", account_id=account_id)
            return
            
        user = await db.get(User, account.user_id)
        
        # Idempotency: skip if this provider message was already processed.
        existing_result = await db.execute(
            select(EmailRecord).where(
                EmailRecord.account_id == account.id,
                EmailRecord.provider_message_id == message_id,
            )
        )
        if existing_result.scalar_one_or_none():
            log.info("Duplicate Gmail webhook ignored", account_id=account_id, message_id=message_id)
            return

        connector = GmailConnector(account)
        raw_msg = connector.get_message(message_id)
        parsed = connector.parse_message(raw_msg)

        received_at = datetime.now(timezone.utc)
        raw_date = parsed.get("date")
        if raw_date:
            try:
                parsed_dt = parsedate_to_datetime(raw_date)
                received_at = parsed_dt.astimezone(timezone.utc) if parsed_dt.tzinfo else parsed_dt.replace(tzinfo=timezone.utc)
            except Exception:
                log.warning("Could not parse email date; using current time", message_id=message_id)

        sender_email = parsed.get("sender_email") or parsed.get("sender") or "unknown@example.com"
        sender_name = parsed.get("sender_name")
        
        # Run importance engine
        score, summary, reply_draft = await process_incoming_email(
            db=db,
            user_id=str(account.user_id),
            tenant_id=str(account.tenant_id),
            sender=sender_email,
            subject=parsed["subject"],
            body=parsed["body"]
        )
        
        # Determine status
        status = "pending"
        if score >= 80:
            status = "alerted"
        
        # Save EmailRecord
        record = EmailRecord(
            tenant_id=account.tenant_id,
            account_id=account.id,
            provider_message_id=parsed["provider_message_id"],
            provider_thread_id=parsed["provider_thread_id"],
            sender_email=sender_email,
            sender_name=sender_name,
            subject=parsed["subject"],
            received_at=received_at,
            ai_summary=summary,
            importance_score=score,
            status=status,
            auto_replied=bool(reply_draft),
            auto_reply_sent_at=datetime.now(timezone.utc) if reply_draft else None,
            auto_reply_content=reply_draft,
        )
        db.add(record)
        await db.flush() # get record.id
        
        # Trigger WhatsApp Notification
        if score >= 80 and user and user.whatsapp_number:
            if reply_draft:
                # Tell user we auto-replied
                notifier.send_auto_reply_notification(
                    to_number=user.whatsapp_number,
                    sender=sender_email,
                    summary=reply_draft[:300],
                    thread_id=parsed["provider_thread_id"],
                    subject=parsed["subject"],
                    original_summary=summary,
                )
            else:
                # Standard manual reply prompt
                notifier.send_alert(
                    to_number=user.whatsapp_number,
                    sender=sender_email,
                    subject=parsed["subject"],
                    summary=summary,
                    score=score,
                    email_id=str(record.id)
                )
        
        # If dry-run is OFF, send the reply via Gmail
        if reply_draft:
            auto_reply_rule_result = await db.execute(
                select(AutoReplyRule).where(AutoReplyRule.user_id == account.user_id)
            )
            auto_reply_rule = auto_reply_rule_result.scalar_one_or_none()
            if auto_reply_rule and not auto_reply_rule.dry_run:
                try:
                    connector.send_reply(
                        thread_id=parsed["provider_thread_id"],
                        to=sender_email,
                        subject=f"Re: {parsed['subject']}",
                        body=reply_draft,
                    )
                    log.info("Auto-reply sent", message_id=message_id, to=sender_email)
                except Exception as e:
                    log.error("Failed to send auto-reply", error=str(e))
        
        await db.commit()
        log.info("Email processed", score=score, message_id=message_id)


async def _process_outlook_webhook_async(account_id: str, message_id: str):
    """Async implementation of the Outlook processing task."""
    async with AsyncSessionLocal() as db:
        account = await db.get(ConnectedAccount, account_id)
        if not account:
            log.error("Account not found", account_id=account_id)
            return

        user = await db.get(User, account.user_id)

        existing_result = await db.execute(
            select(EmailRecord).where(
                EmailRecord.account_id == account.id,
                EmailRecord.provider_message_id == message_id,
            )
        )
        if existing_result.scalar_one_or_none():
            log.info("Duplicate Outlook webhook ignored", account_id=account_id, message_id=message_id)
            return

        connector = OutlookConnector(account)
        raw_msg = await connector.get_message(message_id)
        parsed = connector.parse_message(raw_msg)
        
        # Commit any token refresh that may have occurred
        db.add(account)
        await db.commit()

        received_at = datetime.now(timezone.utc)
        raw_date = parsed.get("date")
        if raw_date:
            try:
                received_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                log.warning("Could not parse Outlook date; using current time", message_id=message_id)

        sender_text = parsed.get("sender", "Unknown")
        sender_name = None
        sender_email = sender_text
        if "<" in sender_text and ">" in sender_text:
            sender_name, sender_email = sender_text.rsplit("<", 1)
            sender_name = sender_name.strip() or None
            sender_email = sender_email.strip().rstrip(">")

        score, summary, reply_draft = await process_incoming_email(
            db=db,
            user_id=str(account.user_id),
            tenant_id=str(account.tenant_id),
            sender=sender_email,
            subject=parsed["subject"],
            body=parsed["body"],
        )

        status = "pending"
        if score >= 80:
            status = "alerted"

        record = EmailRecord(
            tenant_id=account.tenant_id,
            account_id=account.id,
            provider_message_id=parsed["provider_message_id"],
            provider_thread_id=parsed["provider_thread_id"],
            sender_email=sender_email,
            sender_name=sender_name,
            subject=parsed["subject"],
            received_at=received_at,
            ai_summary=summary,
            importance_score=score,
            status=status,
            auto_replied=bool(reply_draft),
            auto_reply_sent_at=datetime.now(timezone.utc) if reply_draft else None,
            auto_reply_content=reply_draft,
        )
        db.add(record)
        await db.flush()

        if score >= 80 and user and user.whatsapp_number:
            if reply_draft:
                notifier.send_auto_reply_notification(
                    to_number=user.whatsapp_number,
                    sender=sender_email,
                    summary=reply_draft[:200] + "...",
                    thread_id=parsed["provider_thread_id"],
                )
            else:
                notifier.send_alert(
                    to_number=user.whatsapp_number,
                    sender=sender_email,
                    subject=parsed["subject"],
                    summary=summary,
                    score=score,
                    email_id=str(record.id),
                )

        # If dry-run is OFF, send the reply via Outlook
        if reply_draft:
            auto_reply_rule_result = await db.execute(
                select(AutoReplyRule).where(AutoReplyRule.user_id == account.user_id)
            )
            auto_reply_rule = auto_reply_rule_result.scalar_one_or_none()
            if auto_reply_rule and not auto_reply_rule.dry_run:
                try:
                    await connector.send_reply(
                        message_id=parsed["provider_message_id"],
                        body=reply_draft,
                    )
                    log.info("Auto-reply sent via Outlook", message_id=message_id, to=sender_email)
                except Exception as e:
                    log.error("Failed to send Outlook auto-reply", error=str(e))

        await db.commit()
        log.info("Outlook email processed", score=score, message_id=message_id)

@celery_app.task(name="process_gmail_webhook")
def process_gmail_webhook(account_id: str, message_id: str):
    """
    Celery task wrapper for async function.
    Fired when a Pub/Sub webhook arrives.
    """
    asyncio.run(_process_gmail_webhook_async(account_id, message_id))


@celery_app.task(name="process_outlook_webhook")
def process_outlook_webhook(account_id: str, message_id: str):
    """Celery task wrapper for Outlook webhook processing."""
    asyncio.run(_process_outlook_webhook_async(account_id, message_id))
