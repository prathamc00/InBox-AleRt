"""
WhatsApp Business API webhook handler for Meta Cloud API.
Handles incoming messages, delivery receipts, and button interactions.
"""
import hmac
import hashlib
import structlog
from fastapi import APIRouter, Request, Response, BackgroundTasks, HTTPException
from sqlalchemy import select
from db.session import AsyncSessionLocal
from models.user import User
from models.email_record import EmailRecord
from core.config import settings

log = structlog.get_logger()
router = APIRouter(prefix="/api/whatsapp/meta", tags=["whatsapp"])


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify that the webhook request came from Meta.
    Signature format: sha256=<hash>
    Uses WHATSAPP_APP_SECRET (the Meta App Secret, not the verify token).
    Returns False if app secret is not configured — never silently accepts.
    """
    secret = settings.WHATSAPP_APP_SECRET.strip()
    # Reject placeholder values that haven't been configured yet
    if not secret or secret in ("your_meta_app_secret", "placeholder"):
        log.error(
            "WhatsApp webhook signature verification skipped: "
            "WHATSAPP_APP_SECRET is not configured. Set it in Render env vars."
        )
        # In debug mode allow through so local development works without app secret.
        # In production this means all webhook POSTs are rejected until configured.
        return settings.DEBUG

    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Remove 'sha256=' prefix if present
    if signature.startswith("sha256="):
        signature = signature[7:]

    return hmac.compare_digest(expected_signature, signature)


async def process_whatsapp_message(from_number: str, message_text: str, button_id: str = None):
    """
    Background task to process incoming WhatsApp messages.
    Handles both text replies and button interactions.
    """
    # Normalize phone number
    phone = from_number.replace("+", "").strip()
    
    async with AsyncSessionLocal() as db:
        # Find user by phone number (support both with and without leading '+')
        user_result = await db.execute(
            select(User).where(
                (User.whatsapp_number == phone) |
                (User.whatsapp_number == f"+{phone}")
            )
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            log.warning("WhatsApp message from unknown number", phone=phone)
            return
        
        # Check if button_id is a direct cancel action for a specific email ID
        email = None
        if button_id and button_id.startswith("cancel_reply_"):
            try:
                email_id_str = button_id.replace("cancel_reply_", "")
                import uuid
                email_id = uuid.UUID(email_id_str)
                email_result = await db.execute(
                    select(EmailRecord).where(EmailRecord.id == email_id)
                )
                email = email_result.scalar_one_or_none()
                if email:
                    log.info("Direct email lookup succeeded for cancel payload", email_id=email.id)
            except Exception as e:
                log.error("Failed to parse email ID from cancel payload", error=str(e), payload=button_id)
        
        if not email:
            # Find most recent alerted email
            email_result = await db.execute(
                select(EmailRecord)
                .where(EmailRecord.tenant_id == user.tenant_id)
                .where(EmailRecord.status == "alerted")
                .order_by(EmailRecord.created_at.desc())
                .limit(1)
            )
            email = email_result.scalar_one_or_none()
        
        if not email:
            log.info("No actionable email found", user_id=user.id)
            return
        
        # Handle button interactions
        if button_id:
            if button_id.startswith("cancel_reply_"):
                email.status = "cancelled"
                log.info("Auto-reply cancelled via button click", email_id=email.id)
                from whatsapp.meta_notifier import meta_notifier
                meta_notifier._send_text(
                    to_number=user.whatsapp_number,
                    text=f"Auto-reply to '{email.subject}' has been cancelled."
                )
            elif button_id.startswith("reply_1_"):
                reply_text = "Thanks, received."
                email.status = "manual_replied"
                log.info("Quick reply 1 triggered", email_id=email.id)
                
            elif button_id.startswith("reply_2_"):
                reply_text = "Will review this today."
                email.status = "manual_replied"
                log.info("Quick reply 2 triggered", email_id=email.id)
                
            elif button_id.startswith("snooze_"):
                email.status = "snoozed"
                log.info("Email snoozed", email_id=email.id)
        
        # Handle text messages
        elif message_text:
            text_lower = message_text.strip().lower()
            
            if text_lower in ["1", "thanks", "received"]:
                email.status = "manual_replied"
                log.info("Manual reply via text", email_id=email.id)
                
            elif text_lower in ["2", "review", "will review"]:
                email.status = "manual_replied"
                log.info("Manual reply via text", email_id=email.id)
                
            elif text_lower in ["3", "snooze"]:
                email.status = "snoozed"
                log.info("Email snoozed via text", email_id=email.id)
                
            elif text_lower.startswith("cancel"):
                # Handle auto-reply cancellation
                email.status = "cancelled"
                log.info("Cancel request received via text", email_id=email.id)
                from whatsapp.meta_notifier import meta_notifier
                meta_notifier._send_text(
                    to_number=user.whatsapp_number,
                    text=f"Auto-reply to '{email.subject}' has been cancelled."
                )
        
        await db.commit()


@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Webhook verification endpoint for Meta.
    Meta sends a GET request with challenge token during setup.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        log.info("WhatsApp webhook verified")
        return Response(content=challenge, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive incoming WhatsApp messages and status updates.
    Meta sends POST requests with message data.
    """
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    
    if not verify_webhook_signature(body, signature):
        log.warning("Invalid webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Parse webhook payload
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Process webhook entries
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            
            # Handle incoming messages
            messages = value.get("messages", [])
            for message in messages:
                from_number = message.get("from")
                message_type = message.get("type")
                
                # Handle text messages
                if message_type == "text":
                    text = message.get("text", {}).get("body", "")
                    background_tasks.add_task(
                        process_whatsapp_message,
                        from_number,
                        text
                    )
                
                # Handle quick reply buttons from template messages (type: "button")
                elif message_type == "button":
                    button_data = message.get("button", {})
                    button_payload = button_data.get("payload")
                    background_tasks.add_task(
                        process_whatsapp_message,
                        from_number,
                        None,
                        button_payload
                    )
                
                # Handle interactive buttons
                elif message_type == "interactive":
                    button_reply = message.get("interactive", {}).get("button_reply", {})
                    button_id = button_reply.get("id")
                    background_tasks.add_task(
                        process_whatsapp_message,
                        from_number,
                        None,
                        button_id
                    )
            
            # Handle status updates (delivered, read, failed)
            statuses = value.get("statuses", [])
            for status in statuses:
                message_id = status.get("id")
                status_type = status.get("status")
                log.info(
                    "Message status update",
                    message_id=message_id,
                    status=status_type
                )
    
    return {"status": "ok"}
