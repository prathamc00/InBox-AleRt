import base64
import email
from email.utils import parseaddr
from typing import Any, Dict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from core.config import settings
from core.security import decrypt_token
from models.account import ConnectedAccount


class GmailConnector:
    def __init__(self, account: ConnectedAccount):
        self.account = account
        self.creds = self._get_credentials()
        self.service = build("gmail", "v1", credentials=self.creds)

    def _get_credentials(self) -> Credentials:
        access_token = decrypt_token(self.account.encrypted_access_token)
        refresh_token = (
            decrypt_token(self.account.encrypted_refresh_token)
            if self.account.encrypted_refresh_token
            else None
        )

        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )

    def watch(self) -> Dict[str, Any]:
        """Subscribe to push notifications via Google Cloud Pub/Sub."""
        topic_name = f"projects/{settings.GOOGLE_CLOUD_PROJECT}/topics/inboxalert-gmail"
        request = {"labelIds": ["INBOX"], "topicName": topic_name}
        return self.service.users().watch(userId="me", body=request).execute()

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """Fetch full email message including raw payload."""
        return (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="raw")
            .execute()
        )

    def list_message_ids_since(self, start_history_id: str) -> list[str]:
        """Return newly added Gmail message IDs since a known history ID."""
        response = (
            self.service.users()
            .history()
            .list(userId="me", startHistoryId=start_history_id, historyTypes=["messageAdded"])
            .execute()
        )

        message_ids: list[str] = []
        for event in response.get("history", []):
            for item in event.get("messagesAdded", []):
                msg = item.get("message", {})
                message_id = msg.get("id")
                if message_id:
                    message_ids.append(message_id)
        return message_ids

    def list_recent_message_ids(self, limit: int = 10) -> list[str]:
        """Return recent Inbox message IDs for manual sync fallback."""
        response = (
            self.service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=max(1, min(limit, 50)))
            .execute()
        )
        return [m["id"] for m in response.get("messages", []) if m.get("id")]

    def parse_message(self, message: Dict[str, Any]) -> Dict[str, str]:
        """Parse raw RFC 2822 email payload into structured dict."""
        raw_b64 = message.get("raw", "")
        msg_bytes = base64.urlsafe_b64decode(raw_b64)
        mime_msg = email.message_from_bytes(msg_bytes)

        subject = mime_msg.get("Subject", "No Subject")
        sender = mime_msg.get("From", "Unknown Sender")
        sender_name, sender_email = parseaddr(sender)
        sender_email = sender_email or sender
        sender_name = sender_name or None
        date = mime_msg.get("Date", "")

        body = ""
        if mime_msg.is_multipart():
            for part in mime_msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" not in content_disposition:
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode("utf-8", errors="replace")
        else:
            payload = mime_msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")

        return {
            "provider_message_id": message["id"],
            "provider_thread_id": message["threadId"],
            "subject": subject,
            "sender": sender,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "date": date,
            "body": body,
        }

    def send_reply(self, thread_id: str, to: str, subject: str, body: str) -> None:
        """Send a reply via Gmail."""
        message_str = f"To: {to}\nSubject: {subject}\nIn-Reply-To: {thread_id}\n\n{body}"
        encoded_message = base64.urlsafe_b64encode(message_str.encode("utf-8")).decode("utf-8")
        raw_message = {"raw": encoded_message, "threadId": thread_id}
        self.service.users().messages().send(userId="me", body=raw_message).execute()

