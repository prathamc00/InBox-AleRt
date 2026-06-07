"""
Smart Reply Engine using Google Gemini.
Generates an auto-reply based on user's tone preference.
"""
import asyncio
import httpx
import structlog
from core.config import settings

log = structlog.get_logger()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

PROMPT_TEMPLATE = """
You are drafting an email reply on behalf of a user. 

USER'S DESIRED TONE: {tone}

ORIGINAL EMAIL:
From: {sender}
Subject: {subject}
Body: {body}

INSTRUCTIONS:
1. Write a direct, polite reply to the original email.
2. Maintain the requested tone.
3. Do not include placeholders like [Your Name] unless absolutely necessary.
4. Keep it concise.
5. Respond ONLY with the raw text of the email reply. No pleasantries directed at me, no JSON, just the email body.
"""

async def generate_auto_reply(sender: str, subject: str, body: str, tone: str = "professional") -> str:
    """
    Calls Gemini to draft an automatic reply.
    """
    if not settings.GEMINI_API_KEY:
        return "Thank you for your email. I am currently away and will respond shortly."

    safe_body = body[:2000].replace("{", "").replace("}", "")
    prompt = PROMPT_TEMPLATE.format(
        tone=tone,
        sender=sender, 
        subject=subject, 
        body=safe_body
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(3):
            try:
                response = await client.post(
                    f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response else 0
                if status in {429, 500, 502, 503, 504} and attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                err_text = exc.response.text[:100] if exc.response else str(exc)
                log.error("Gemini auto-reply failed", status_code=status, error=str(exc))
                return f"Error drafting reply: HTTP {status} - {err_text}"
            except Exception as exc:
                log.error("Gemini auto-reply failed", error=str(exc))
                return f"Error drafting reply: {str(exc)}"

    return "Error drafting reply: Request failed."
