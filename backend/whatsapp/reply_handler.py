import re
from fastapi import APIRouter, Request, Response, BackgroundTasks
from sqlalchemy import select
from db.session import AsyncSessionLocal
from models.user import User
from models.email_record import EmailRecord
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

# Predefined quick replies mapping
QUICK_REPLIES = {
    "1": "Thanks, received.",
    "2": "Will review this today.",
}

async def process_whatsapp_reply(from_number: str, body: str):
    """
    Background task to process the user's SMS/WhatsApp reply.
    """
    # Extract the phone number (remove 'whatsapp:' prefix)
    phone = from_number.replace("whatsapp:", "")
    
    # 1. Parse the incoming text
    body = body.strip().lower()
    
    # 2. Extract email ID from the message context 
    # (In a real app, Twilio maintains session state or we parse the Quoted Message ID)
    # For this MVP, we assume the user is replying to the most recent alerted email.
    
    async with AsyncSessionLocal() as db:
        # Find the user by phone number
        user_result = await db.execute(select(User).where(User.whatsapp_number == phone))
        user = user_result.scalar_one_or_none()
        
        if not user:
            log.warning("Received WhatsApp reply from unknown number", phone=phone)
            return

        # Find their most recent pending/alerted email
        email_result = await db.execute(
            select(EmailRecord)
            .where(EmailRecord.tenant_id == user.tenant_id)
            .where(EmailRecord.status == "alerted")
            .order_by(EmailRecord.created_at.desc())
            .limit(1)
        )
        email = email_result.scalar_one_or_none()
        
        if not email:
            log.info("No actionable email found for user", user_id=user.id)
            return

        # 3. Handle the reply intent
        if body in QUICK_REPLIES:
            reply_text = QUICK_REPLIES[body]
            # TODO: Fetch the ConnectedAccount and trigger connector.send_reply(reply_text)
            email.status = "manual_replied"
            log.info("Triggered manual reply", email_id=email.id, reply=reply_text)
            
        elif body == "3" or "snooze" in body:
            email.status = "snoozed"
            log.info("Snoozed email", email_id=email.id)
            
        elif body.startswith("cancel"):
            # Handle auto-reply cancellation window logic
            # e.cancel_auto_reply()
            pass
            
        await db.commit()


@router.post("/incoming")
async def twilio_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Twilio to send incoming WhatsApp messages.
    Must return 200 OK immediately with TwiML (or empty string).
    """
    # Parse form data from Twilio
    form_data = await request.form()
    
    from_number = form_data.get("From", "")
    body = form_data.get("Body", "")
    
    log.info("Received WhatsApp message", from_number=from_number, body=body)
    
    # Process the reply in the background so Twilio doesn't timeout
    background_tasks.add_task(process_whatsapp_reply, from_number, body)
    
    # Return empty TwiML response
    return Response(content="<Response></Response>", media_type="application/xml")
