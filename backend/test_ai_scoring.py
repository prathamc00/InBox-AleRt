import asyncio
import os
import sys

# Ensure correct path imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine.scorer import process_incoming_email
from db.session import AsyncSessionLocal
from core.config import settings

async def main():
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your_"):
        print("Error: GEMINI_API_KEY is not configured in .env")
        return

    print(f"Testing with API Key: {settings.GEMINI_API_KEY[:8]}...")
    
    # Simulating a high-priority HR job email
    sender = "hr@startup.com"
    subject = "InboxAlert Interview Scheduling: Senior Developer position"
    body = """
    Hi Prathmesh,
    
    We reviewed your profile and want to move forward with scheduling the technical interview.
    Please let us know your availability for a 45-minute call tomorrow.
    
    Best regards,
    Hiring Team
    """
    
    async with AsyncSessionLocal() as db:
        print("Processing simulated email through rules and Gemini AI...")
        try:
            score, summary, reply_draft = await process_incoming_email(
                db=db,
                user_id="00000000-0000-0000-0000-000000000000",  # Dummy UUID
                tenant_id="00000000-0000-0000-0000-000000000000", # Dummy UUID
                sender=sender,
                subject=subject,
                body=body
            )
            print("\n=== Test Results ===")
            print(f"Importance Score: {score}/100")
            print(f"AI Summary: {summary}")
            if reply_draft:
                print(f"Auto-reply Drafted:\n{reply_draft}")
            else:
                print("No auto-reply drafted (score below threshold or auto-reply disabled).")
        except Exception as e:
            print(f"Error executing AI engine: {e}")

if __name__ == "__main__":
    asyncio.run(main())
