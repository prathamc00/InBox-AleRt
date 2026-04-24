from typing import Any, Dict, Optional
from datetime import datetime, timedelta, timezone

import httpx
import msal
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import decrypt_token, encrypt_token
from models.account import ConnectedAccount


class OutlookConnector:
    def __init__(self, account: ConnectedAccount, db: Optional[AsyncSession] = None):
        self.account = account
        self.db = db
        self.access_token = decrypt_token(self.account.encrypted_access_token)
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _refresh_token_if_needed(self):
        """Refresh the access token if it's expired or about to expire."""
        if not self.account.token_expires_at:
            return
        
        # Check if token is expired or will expire in the next 5 minutes
        now = datetime.now(timezone.utc)
        if self.account.token_expires_at > now + timedelta(minutes=5):
            return
        
        # Token needs refresh
        if not self.account.encrypted_refresh_token:
            raise Exception("No refresh token available")
        
        refresh_token = decrypt_token(self.account.encrypted_refresh_token)
        
        # Use MSAL to refresh the token
        msal_app = msal.ConfidentialClientApplication(
            settings.MICROSOFT_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}",
            client_credential=settings.MICROSOFT_CLIENT_SECRET,
        )
        
        result = msal_app.acquire_token_by_refresh_token(
            refresh_token,
            scopes=["User.Read", "Mail.Read", "Mail.Send"],
        )
        
        if "error" in result:
            raise Exception(f"Token refresh failed: {result.get('error_description', 'Unknown error')}")
        
        # Update the account with new tokens
        new_access_token = result["access_token"]
        new_refresh_token = result.get("refresh_token", refresh_token)
        expires_in = result.get("expires_in", 3600)
        
        self.account.encrypted_access_token = encrypt_token(new_access_token)
        self.account.encrypted_refresh_token = encrypt_token(new_refresh_token)
        self.account.token_expires_at = now + timedelta(seconds=expires_in)
        
        # Update instance variables
        self.access_token = new_access_token
        self.headers["Authorization"] = f"Bearer {self.access_token}"

    async def create_subscription(self, webhook_url: str) -> Dict[str, Any]:
        """Subscribe to new message notifications via Microsoft Graph."""
        await self._refresh_token_if_needed()
        expiration = datetime.now(timezone.utc) + timedelta(days=2)
        payload = {
            "changeType": "created",
            "notificationUrl": webhook_url,
            "resource": "me/mailFolders('Inbox')/messages",
            "expirationDateTime": expiration.isoformat().replace("+00:00", "Z"),
            "clientState": settings.OUTLOOK_WEBHOOK_CLIENT_STATE,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/subscriptions",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Fetch specific message details."""
        await self._refresh_token_if_needed()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me/messages/{message_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_recent_message_ids(self, limit: int = 10) -> list[str]:
        """Return recent Outlook inbox message IDs for manual sync fallback."""
        await self._refresh_token_if_needed()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me/mailFolders/Inbox/messages",
                headers=self.headers,
                params={"$select": "id", "$top": max(1, min(limit, 50))},
            )
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("value", []) if m.get("id")]

    def parse_message(self, message: Dict[str, Any]) -> Dict[str, str]:
        """Parse Graph API message format."""
        sender_email = message.get("sender", {}).get("emailAddress", {}).get("address", "Unknown")
        sender_name = message.get("sender", {}).get("emailAddress", {}).get("name", sender_email)
        
        # Outlook gives HTML body or text; we'll prefer text preview if full parsing is complex for this MVP
        body = message.get("bodyPreview", "")

        return {
            "provider_message_id": message["id"],
            "provider_thread_id": message.get("conversationId", ""),
            "subject": message.get("subject", "No Subject"),
            "sender": f"{sender_name} <{sender_email}>",
            "date": message.get("receivedDateTime", ""),
            "body": body,
        }

    async def send_reply(self, message_id: str, body: str) -> None:
        """Send a reply via Outlook."""
        await self._refresh_token_if_needed()
        payload = {"comment": body}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/me/messages/{message_id}/reply",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
