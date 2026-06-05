import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.session import AsyncSessionLocal
from models.user import User
from sqlalchemy import select
from whatsapp.meta_notifier import meta_notifier

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.whatsapp_number != None))
        user = result.scalars().first()
        
        if not user:
            print("No user with a WhatsApp number found in the database.")
            return
            
        print(f"Sending test notification to: {user.whatsapp_number}")
        
        ok, error_detail = meta_notifier.send_alert(
            to_number=user.whatsapp_number,
            sender="hr@company.com",
            subject="Interview Request",
            summary="This is a test notification for your database.",
            score=95,
            email_id="test-id"
        )
        
        if ok:
            print("Success! WhatsApp notification sent.")
        else:
            print(f"\n=== Meta Error Response ===")
            print(error_detail)

if __name__ == "__main__":
    asyncio.run(main())
