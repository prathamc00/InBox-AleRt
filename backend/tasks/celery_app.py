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
from whatsapp.meta_notifier import meta_notifier as notifier

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
        if score >= 50:
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
            auto_reply_sent_at=None,
            auto_reply_content=reply_draft,
        )
        db.add(record)
        await db.flush() # get record.id
        
        # Check if dry-run is OFF and rule is enabled
        should_auto_reply = False
        cancel_seconds = 60
        if reply_draft:
            auto_reply_rule_result = await db.execute(
                select(AutoReplyRule).where(AutoReplyRule.user_id == account.user_id)
            )
            auto_reply_rule = auto_reply_rule_result.scalar_one_or_none()
            if auto_reply_rule and auto_reply_rule.is_enabled and not auto_reply_rule.dry_run:
                should_auto_reply = True
                cancel_seconds = auto_reply_rule.cancel_window_seconds

        # Trigger WhatsApp Notification
        if score >= 50 and user and user.whatsapp_number:
            if should_auto_reply:
                notifier.send_auto_reply_template_alert(
                    to_number=user.whatsapp_number,
                    sender=sender_email,
                    subject=parsed["subject"],
                    reply_draft=reply_draft,
                    cancel_seconds=cancel_seconds,
                    email_record_id=str(record.id),
                    score=score,
                )
            else:
                notifier.send_alert_template(
                    to_number=user.whatsapp_number,
                    sender=sender_email,
                    subject=parsed["subject"],
                    summary=summary or "",
                    score=score,
                )
        
        # Schedule the auto-reply instead of sending it immediately
        if should_auto_reply:
            try:
                send_delayed_auto_reply.apply_async(
                    args=[str(record.id)],
                    countdown=cancel_seconds
                )
                log.info("Scheduled delayed auto-reply task for Gmail", record_id=str(record.id), countdown=cancel_seconds)
            except Exception as exc:
                log.error("Failed to enqueue auto-reply in Celery", error=str(exc))
        
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
        if score >= 50:
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
            auto_reply_sent_at=None,
            auto_reply_content=reply_draft,
        )
        db.add(record)
        await db.flush()

        # Check if dry-run is OFF and rule is enabled
        should_auto_reply = False
        cancel_seconds = 60
        if reply_draft:
            auto_reply_rule_result = await db.execute(
                select(AutoReplyRule).where(AutoReplyRule.user_id == account.user_id)
            )
            auto_reply_rule = auto_reply_rule_result.scalar_one_or_none()
            if auto_reply_rule and auto_reply_rule.is_enabled and not auto_reply_rule.dry_run:
                should_auto_reply = True
                cancel_seconds = auto_reply_rule.cancel_window_seconds

        # Trigger WhatsApp Notification
        if score >= 50 and user and user.whatsapp_number:
            if should_auto_reply:
                notifier.send_auto_reply_template_alert(
                    to_number=user.whatsapp_number,
                    sender=sender_email,
                    subject=parsed["subject"],
                    reply_draft=reply_draft,
                    cancel_seconds=cancel_seconds,
                    email_record_id=str(record.id),
                    score=score,
                )
            else:
                notifier.send_alert_template(
                    to_number=user.whatsapp_number,
                    sender=sender_email,
                    subject=parsed["subject"],
                    summary=summary or "",
                    score=score,
                )

        # Schedule the auto-reply instead of sending it immediately
        if should_auto_reply:
            try:
                send_delayed_auto_reply.apply_async(
                    args=[str(record.id)],
                    countdown=cancel_seconds
                )
                log.info("Scheduled delayed auto-reply task for Outlook", record_id=str(record.id), countdown=cancel_seconds)
            except Exception as exc:
                log.error("Failed to enqueue auto-reply in Celery", error=str(exc))

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


@celery_app.task(name="send_delayed_auto_reply")
def send_delayed_auto_reply(record_id: str):
    """
    Celery task that runs after cancel_window_seconds.
    Checks if the email record was cancelled; if not, sends the reply.
    """
    asyncio.run(_send_delayed_auto_reply_async(record_id))


async def _send_delayed_auto_reply_async(record_id: str):
    import uuid
    async with AsyncSessionLocal() as db:
        record = await db.get(EmailRecord, uuid.UUID(record_id))
        if not record:
            log.error("Email record not found for delayed auto-reply", record_id=record_id)
            return

        if record.status == "cancelled":
            log.info("Delayed auto-reply cancelled by user, skipping send", record_id=record_id)
            return

        account = await db.get(ConnectedAccount, record.account_id)
        if not account:
            log.error("Account not found for auto-reply", account_id=record.account_id)
            return

        user = await db.get(User, account.user_id)
        if not user:
            log.error("User not found for auto-reply", user_id=account.user_id)
            return

        # Double check that the rule is still enabled and dry_run is still False
        from models.auto_reply import AutoReplyRule
        rule_result = await db.execute(
            select(AutoReplyRule).where(AutoReplyRule.user_id == user.id)
        )
        rule = rule_result.scalar_one_or_none()
        if not rule or not rule.is_enabled or rule.dry_run:
            log.info("Auto-reply rule disabled or in dry-run, skipping send", record_id=record_id)
            return

        try:
            if account.provider == "gmail":
                connector = GmailConnector(account)
                connector.send_reply(
                    thread_id=record.provider_thread_id,
                    to=record.sender_email,
                    subject=f"Re: {record.subject}",
                    body=record.auto_reply_content,
                )
                log.info("Delayed auto-reply sent via Gmail", record_id=record_id)
            elif account.provider == "outlook":
                connector = OutlookConnector(account)
                await connector.send_reply(
                    message_id=record.provider_message_id,
                    body=record.auto_reply_content,
                )
                log.info("Delayed auto-reply sent via Outlook", record_id=record_id)

            record.status = "auto_replied"
            record.auto_reply_sent_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as e:
            log.error("Failed to send delayed auto-reply", record_id=record_id, error=str(e))
