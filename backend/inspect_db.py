import asyncio
from db.session import AsyncSessionLocal
from models.account import ConnectedAccount
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ConnectedAccount))
        accounts = result.scalars().all()
        for a in accounts:
            print(f"ID: {a.id}")
            print(f"Email: {a.email_address}")
            print(f"Encrypted Access Token (truncated): {a.encrypted_access_token[:20]}...")
            if a.encrypted_refresh_token:
                print(f"Encrypted Refresh Token (truncated): {a.encrypted_refresh_token[:20]}...")
            print("---")

if __name__ == "__main__":
    asyncio.run(main())
