"""
Fast, rule-based scoring engine.
Runs before AI. Can boost or penalize scores based on simple heuristics
to save API costs on obvious spam or obvious priority.
"""
import re
from typing import Dict, Any

URGENT_KEYWORDS = [
    r"\burgent\b",
    r"\basap\b",
    r"\baction required\b",
    r"\bimportant\b",
    r"\bdeadline\b",
    r"\bsignature needed\b",
    r"\bpriority\b",
]

DISCOUNT_KEYWORDS = [
    r"\bnewsletter\b",
    r"\bunsubscribe\b",
    r"\bpromo\b",
    r"\bspecial offer\b",
    r"\bmarketing\b",
]

def score_by_rules(subject: str, sender: str, body: str) -> Dict[str, Any]:
    """
    Returns a dict with a 'base_score' modification and 'bypass_ai' boolean.
    If 'bypass_ai' is True, we don't even send to Gemini (saves money).
    """
    subject_lower = subject.lower()
    body_lower = body.lower()
    
    score_modifier = 0
    bypass_ai = False
    
    # 1. Obvious newsletters/promos (Heavily penalize)
    for kw in DISCOUNT_KEYWORDS:
        if re.search(kw, subject_lower) or re.search(kw, body_lower[:500]):
            score_modifier -= 50
            # If it's a newsletter, we don't need AI to tell us it's not important
            bypass_ai = True
            return {"score_modifier": score_modifier, "bypass_ai": bypass_ai, "reason": "Rule: Promotional/Newsletter"}

    # 2. Urgent keywords (Boost)
    for kw in URGENT_KEYWORDS:
        if re.search(kw, subject_lower):
            score_modifier += 30
            break

    # 3. Known system emails (No-reply)
    if "no-reply" in sender.lower() or "noreply" in sender.lower():
        score_modifier -= 20
        # Wait, some no-reply are important alerts (like AWS). We let AI judge if it's an alert.

    return {"score_modifier": score_modifier, "bypass_ai": bypass_ai, "reason": "Rule: Keyword analysis"}
