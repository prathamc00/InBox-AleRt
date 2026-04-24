"""
AI Scoring Engine using Google Gemini.
Evaluates email subject and body, returns a score 0-100 and a 3-line summary.
"""
import asyncio
import json
import httpx
from typing import Dict, Any
import structlog
from core.config import settings

log = structlog.get_logger()

# In production, we'd use the official google-genai SDK, but for async speed
# in FastAPI/Celery, raw HTTPx to the Gemini REST API is extremely fast.
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

PROMPT_TEMPLATE = """
You are an elite executive assistant AI. 
Your job is to read incoming emails, score their importance (0-100), and write a concise 1-3 line summary.

SCORING GUIDELINES:
90-100: Critical, requires immediate action (contracts, outages, VIP clients, urgent meetings).
70-89: Important, needs reading today but not immediate (team updates, standard client emails, direct questions).
40-69: Routine (receipts, calendar accepts, minor FYI).
0-39: Junk, newsletters, cold sales, automated spam.

EMAIL METADATA:
Sender: {sender}
Subject: {subject}
Body Snippet: {body}

OUTPUT FORMAT:
You MUST respond with valid JSON only, exactly matching this schema:
{{
  "score": <integer 0-100>,
  "summary": "<1-3 lines summarizing the core request or point>"
}}
"""

async def get_ai_score_and_summary(sender: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Calls Gemini to score and summarize the email.
    """
    if not settings.GEMINI_API_KEY:
        # Fallback if no key is set
        return {"score": 50, "summary": "AI processing disabled (No API Key)."}

    # Sanitize and truncate body to prevent prompt injection and save tokens
    safe_body = body[:2000].replace("{", "").replace("}", "")
    
    prompt = PROMPT_TEMPLATE.format(
        sender=sender, 
        subject=subject, 
        body=safe_body
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(3):
            try:
                response = await client.post(
                    f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                # Parse Gemini response
                text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                result = json.loads(text_response)

                score_raw = result.get("score", 50)
                try:
                    score = int(score_raw)
                except (TypeError, ValueError):
                    score = 50
                score = max(0, min(100, score))

                summary = str(result.get("summary", "Could not generate summary.")).strip()
                if not summary:
                    summary = "Could not generate summary."

                return {
                    "score": score,
                    "summary": summary,
                }
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response else 0
                if status in {429, 500, 502, 503, 504} and attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                log.error("Gemini scoring failed", status_code=status, error=str(exc))
                return {"score": 50, "summary": "Error during AI analysis."}
            except Exception as exc:
                log.error("Gemini scoring failed", error=str(exc))
                return {"score": 50, "summary": "Error during AI analysis."}

    return {"score": 50, "summary": "Error during AI analysis."}
