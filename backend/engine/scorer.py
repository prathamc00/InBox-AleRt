"""
The Orchestrator. Coordinates rules, AI scoring, and auto-reply.
"""
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from engine.rules import score_by_rules
from engine.ai_score import get_ai_score_and_summary
from ai.smart_reply import generate_auto_reply
from models.auto_reply import AutoReplyRule
from models.email_record import EmailRecord

async def process_incoming_email(
    db: AsyncSession, 
    user_id: str, 
    tenant_id: str,
    sender: str, 
    subject: str, 
    body: str
) -> Tuple[int, str, str | None]:
    """
    1. Run rule engine.
    2. Run AI engine (if not bypassed).
    3. Calculate final score.
    4. Check Auto-Reply rules (including business hours and daily limit).
    5. Draft reply if needed.
    
    Returns: (final_score, ai_summary, auto_reply_draft)
    """
    from uuid import UUID

    # 1. Rule Engine
    rule_result = score_by_rules(subject, sender, body)
    
    final_score = 50
    ai_summary = rule_result.get("reason", "Processed by rule engine.")
    
    # 2. AI Engine
    if not rule_result["bypass_ai"]:
        ai_result = await get_ai_score_and_summary(sender, subject, body)
        final_score = ai_result["score"]
        ai_summary = ai_result["summary"]
        
    # Apply rule modifier
    final_score += rule_result["score_modifier"]
    final_score = max(0, min(100, final_score))  # Clamp 0-100
    
    auto_reply_draft = None
    
    # 3. Auto-Reply Check
    if final_score >= 80:
        result = await db.execute(
            select(AutoReplyRule).where(AutoReplyRule.user_id == UUID(user_id))
        )
        rule = result.scalar_one_or_none()
        
        if rule and rule.is_enabled and final_score >= rule.min_importance_score:

            # 3a. Business hours check
            if rule.business_hours_only:
                try:
                    from zoneinfo import ZoneInfo
                    tz = ZoneInfo(rule.timezone or "UTC")
                    now = datetime.now(tz)
                    start_h, start_m = map(int, rule.business_hours_start.split(":"))
                    end_h, end_m = map(int, rule.business_hours_end.split(":"))
                    current_minutes = now.hour * 60 + now.minute
                    in_business_hours = (start_h * 60 + start_m) <= current_minutes < (end_h * 60 + end_m)
                    if not in_business_hours:
                        # Outside business hours — skip auto-reply
                        return final_score, ai_summary, None
                except Exception:
                    pass  # If TZ parsing fails, continue without business hours filter

            # 3b. Daily limit check
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            daily_count_result = await db.execute(
                select(func.count(EmailRecord.id)).where(
                    EmailRecord.tenant_id == UUID(tenant_id),
                    EmailRecord.auto_replied == True,
                    EmailRecord.auto_reply_sent_at >= today_start,
                )
            )
            daily_count = daily_count_result.scalar() or 0
            if daily_count >= rule.daily_auto_reply_limit:
                # Daily limit reached — skip auto-reply
                return final_score, ai_summary, None

            # 3c. Draft the reply
            auto_reply_draft = await generate_auto_reply(
                sender=sender, 
                subject=subject, 
                body=body, 
                tone=rule.reply_tone
            )
                
    return final_score, ai_summary, auto_reply_draft
