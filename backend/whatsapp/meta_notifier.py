"""WhatsApp notifier using Meta Cloud API.

Key rules:
- Test messages use Meta's built-in `hello_world` template so they always
  deliver even when there is no open 24-hour conversation window.
- Real alert messages use free-form text, which is valid once the user has
  interacted with the business number (i.e. the 24-hour window is open).
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import structlog

from core.config import settings

log = structlog.get_logger()

_META_API_VERSION = "v21.0"


class MetaNotifier:
    def __init__(self) -> None:
        self.meta_token = settings.WHATSAPP_ACCESS_TOKEN.strip()
        self.meta_phone_id = settings.WHATSAPP_PHONE_NUMBER_ID.strip()

    def send_test_message_result(self, to_number: str) -> tuple[bool, str]:
        """Send a test message.

        Uses the Meta `hello_world` template so it works even without an open
        24-hour conversation window (i.e. the user doesn't need to message first).
        """
        if self._meta_ready():
            log.info("WhatsApp test: sending hello_world template", provider="meta")
            return self._send_meta_template(
                to_number=to_number,
                template_name="hello_world",
                language_code="en_US",
            )
        return False, "No WhatsApp provider is configured. Set Meta credentials."

    def diagnostics(self) -> dict[str, Any]:
        provider = "none"
        if self._meta_ready():
            provider = "meta"
        return {
            "provider": provider,
            "meta_configured": self._meta_ready(),
            "meta_phone_number_id_present": bool(self.meta_phone_id),
            "meta_access_token_present": bool(self.meta_token),
        }

    def send_alert(
        self,
        to_number: str,
        sender: str,
        subject: str,
        summary: str,
        score: int,
        email_id: str,
    ) -> tuple[bool, str]:
        msg = (
            f"InboxAlert: Important email (score {score})\n"
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Summary: {summary}\n"
            f"Email ID: {email_id}"
        )
        return self._send_text(to_number=to_number, text=msg)

    def send_auto_reply_notification(
        self,
        to_number: str,
        sender: str,
        summary: str,
        thread_id: str,
        subject: str | None = None,
        original_summary: str | None = None,
    ) -> tuple[bool, str]:
        parts = [
            "InboxAlert: Auto-reply sent",
            f"From: {sender}",
        ]
        if subject:
            parts.append(f"Subject: {subject}")
        if original_summary:
            parts.append(f"Original summary: {original_summary}")
        parts.append(f"Reply: {summary}")
        parts.append(f"Thread ID: {thread_id}")
        return self._send_text(to_number=to_number, text="\n".join(parts))

    # ── Internal routing ───────────────────────────────────────────────────────

    def _send_text(self, to_number: str, text: str) -> tuple[bool, str]:
        """Send a free-form text message (requires an open 24-h window)."""
        if self._meta_ready():
            log.info("WhatsApp send provider selected", provider="meta")
            return self._send_meta_text(to_number=to_number, text=text)
        return False, "No WhatsApp provider is configured. Set Meta credentials."

    def _meta_ready(self) -> bool:
        return bool(self.meta_token and self.meta_phone_id)

    # ── Meta Cloud API ─────────────────────────────────────────────────────────

    def _meta_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.meta_token}",
            "Content-Type": "application/json",
        }

    def _send_meta_template(
        self,
        to_number: str,
        template_name: str,
        components: list[dict[str, Any]] | None = None,
        language_code: str = "en_US",
    ) -> tuple[bool, str]:
        """Send a pre-approved Meta template message.

        Templates work without an open conversation window — they are the
        correct approach for business-initiated contacts.
        """
        url = f"https://graph.facebook.com/{_META_API_VERSION}/{self.meta_phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number.lstrip("+"),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    url,
                    headers=self._meta_headers(),
                    content=json.dumps(payload),
                )
            data: dict[str, Any] = {}
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}

            log.info("Meta template send response", status=resp.status_code, body=data)

            if 200 <= resp.status_code < 300:
                return True, "sent"

            err = data.get("error", {})
            message = err.get("message") or data.get("raw") or "Unknown Meta error"
            code = err.get("code")
            return False, f"Meta HTTP {resp.status_code} Error ({code}): {message}"
        except Exception as exc:
            log.exception("Failed Meta template send", error=str(exc))
            return False, str(exc)

    def send_alert_template(
        self,
        to_number: str,
        sender: str,
        subject: str,
        summary: str,
        score: int,
    ) -> tuple[bool, str]:
        """Send a standard email alert template."""
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "parameter_name": "email_sender", "text": sender},
                    {"type": "text", "parameter_name": "email_subject", "text": subject},
                    {"type": "text", "parameter_name": "email_summary", "text": summary[:300]},
                ]
            }
        ]
        return self._send_meta_template(
            to_number=to_number,
            template_name="email_alerts",
            components=components,
        )

    def send_auto_reply_template_alert(
        self,
        to_number: str,
        sender: str,
        subject: str,
        reply_draft: str,
        cancel_seconds: int,
        email_record_id: str,
        score: int,
    ) -> tuple[bool, str]:
        """Send an auto-reply notification with a cancel button."""
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "parameter_name": "score", "text": str(score)},
                    {"type": "text", "parameter_name": "sender", "text": sender},
                    {"type": "text", "parameter_name": "subject", "text": subject},
                    {"type": "text", "parameter_name": "reply_draft", "text": reply_draft[:300]},
                    {"type": "text", "parameter_name": "cancel_seconds", "text": str(cancel_seconds)},
                ]
            },
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": "0",
                "parameters": [
                    {
                        "type": "payload",
                        "payload": f"cancel_reply_{email_record_id}"
                    }
                ]
            }
        ]
        return self._send_meta_template(
            to_number=to_number,
            template_name="auto_reply_alerts",
            components=components,
        )


    def _send_meta_text(self, to_number: str, text: str) -> tuple[bool, str]:
        """Send a free-form text message via Meta Cloud API.

        Only works inside a 24-hour conversation window (user must have messaged first).
        """
        url = f"https://graph.facebook.com/{_META_API_VERSION}/{self.meta_phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number.lstrip("+"),
            "type": "text",
            "text": {"body": text},
        }
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    url,
                    headers=self._meta_headers(),
                    content=json.dumps(payload),
                )
            data: dict[str, Any] = {}
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}

            log.info("Meta text send response", status=resp.status_code, body=data)

            if 200 <= resp.status_code < 300:
                return True, "sent"

            err = data.get("error", {})
            message = err.get("message") or data.get("raw") or "Unknown Meta error"
            code = err.get("code")
            return False, f"Meta HTTP {resp.status_code} Error ({code}): {message}"
        except Exception as exc:
            log.exception("Failed Meta text send", error=str(exc))
            return False, str(exc)


meta_notifier = MetaNotifier()
