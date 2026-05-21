import asyncio
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

from core.config import settings
from db.session import AsyncSessionLocal
from models.account import ConnectedAccount
from sqlalchemy import select

async def main():
    print("Checking Microsoft configuration settings...")
    print(f"MICROSOFT_CLIENT_ID: {settings.MICROSOFT_CLIENT_ID}")
    print(f"MICROSOFT_TENANT_ID: {settings.MICROSOFT_TENANT_ID}")
    print(f"MICROSOFT_REDIRECT_URI: {settings.MICROSOFT_REDIRECT_URI}")
    
    print("\nQuerying ConnectedAccount database...")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ConnectedAccount))
            accounts = result.scalars().all()
            print(f"Found {len(accounts)} connected accounts in DB:")
            for acc in accounts:
                print(f"- ID: {acc.id}, Provider: {acc.provider}, Email: {acc.email_address}, Active: {acc.is_active}")
                print(f"  Token expires at: {acc.token_expires_at}")
                print(f"  Outlook Subscription ID: {acc.outlook_subscription_id}")
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    asyncio.run(main())
