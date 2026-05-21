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
    Signature is in format: sha256=<hash>
    """
    if not settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        log.warning("WhatsApp webhook verification disabled")
        return True
    
    expected_signature = hmac.new(
        settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN.encode(),
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
            if button_id.startswith("reply_1_"):
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
                log.info("Cancel request received", email_id=email.id)
        
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
                
                # Handle button replies
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
