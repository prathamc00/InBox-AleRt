"""
The Orchestrator. Coordinates rules, AI scoring, and auto-reply.
"""
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from engine.rules import score_by_rules
from engine.ai_score import get_ai_score_and_summary
from ai.smart_reply import generate_auto_reply
from models.auto_reply import AutoReplyRule

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
    4. Check Auto-Reply rules.
    5. Draft reply if needed.
    
    Returns: (final_score, ai_summary, auto_reply_draft)
    """
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
    final_score = max(0, min(100, final_score)) # Clamp 0-100
    
    auto_reply_draft = None
    
    # 3. Auto-Reply Check
    if final_score >= 80:
        result = await db.execute(select(AutoReplyRule).where(AutoReplyRule.user_id == user_id))
        rule = result.scalar_one_or_none()
        
        if rule and rule.is_enabled:
            # Check threshold and limits
            if final_score >= rule.min_importance_score:
                # Todo: check daily limit and scope here
                
                # Draft the reply
                auto_reply_draft = await generate_auto_reply(
                    sender=sender, 
                    subject=subject, 
                    body=body, 
                    tone=rule.reply_tone
                )
                
    return final_score, ai_summary, auto_reply_draft
