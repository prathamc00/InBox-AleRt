from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from db.session import get_db
from models.user import User
from models.email_record import EmailRecord

router = APIRouter(prefix="/api/emails", tags=["emails"])

@router.get("")
async def get_emails(
    filter_type: str = "important", # important | all | auto_replied | snoozed
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch processed emails for the dashboard.
    """
    query = select(EmailRecord).where(EmailRecord.tenant_id == current_user.tenant_id)

    if filter_type == "important":
        query = query.where(EmailRecord.importance_score >= 80)
    elif filter_type == "auto_replied":
        query = query.where(EmailRecord.auto_replied == True)
    elif filter_type == "snoozed":
        query = query.where(EmailRecord.status == "snoozed")
        
    query = query.order_by(desc(EmailRecord.received_at)).limit(50)
    
    result = await db.execute(query)
    emails = result.scalars().all()
    
    return [
        {
            "id": str(e.id),
            "sender_name": e.sender_name or e.sender_email,
            "sender_email": e.sender_email,
            "subject": e.subject,
            "ai_summary": e.ai_summary,
            "importance_score": e.importance_score,
            "received_at": e.received_at.isoformat(),
            "status": e.status,
            "auto_replied": e.auto_replied,
            "auto_reply_content": e.auto_reply_content,
        }
        for e in emails
    ]
