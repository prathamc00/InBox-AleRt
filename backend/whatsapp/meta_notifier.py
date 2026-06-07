"""WhatsApp notifier using Meta Cloud API.

Key rules:
- Template messages (send_alert_template, send_auto_reply_template_alert) use
  pre-approved Meta templates and work without an open 24-hour conversation
  window.
- For templates with named variables (e.g. {{score}}, {{sender}}, etc.), the
  'parameter_name' field is required in the API payload to map parameters
  correctly to their variables.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from core.config import settings

log = structlog.get_logger()

_META_API_VERSION = "v21.0"


def _sanitize_template_param(val: Any) -> str:
    if val is None:
        return ""
    import re
    s = str(val)
    # Replace newlines, carriage returns, and tabs with spaces
    s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # Replace more than 4 consecutive spaces or multiple spaces with a single space
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


class MetaNotifier:
    def __init__(self) -> None:
        self.meta_token = settings.WHATSAPP_ACCESS_TOKEN.strip()
        self.meta_phone_id = settings.WHATSAPP_PHONE_NUMBER_ID.strip()

    def send_test_message_result(self, to_number: str) -> tuple[bool, str]:
        """Send a test message using the 'email_alerts' template.

        We use email_alerts because it is currently Active on Meta,
        whereas auto_reply_alerts may still be in review.
        """
        if self._meta_ready():
            log.info("WhatsApp test: sending email_alerts template", provider="meta")
            return self.send_alert_template(
                to_number=to_number,
                sender="test@inboxalert.com",
                subject="Test Notification",
                summary="This is a test notification from InboxAlert to verify your WhatsApp configuration.",
                score=100,
                email_id="test",
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

    def _run_sync(self, coro):
        import asyncio
        import threading
        from concurrent.futures import Future

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            result_future = Future()
            def run_in_thread():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    res = new_loop.run_until_complete(coro)
                    result_future.set_result(res)
                except Exception as e:
                    result_future.set_exception(e)
                finally:
                    new_loop.close()
            t = threading.Thread(target=run_in_thread)
            t.start()
            t.join()
            return result_future.result()
        return asyncio.run(coro)

    def _send_meta_template(
        self,
        to_number: str,
        template_name: str,
        components: list[dict[str, Any]] | None = None,
        language_code: str = "en",
    ) -> tuple[bool, str]:
        """Send a pre-approved Meta template message (synchronous wrapper).

        Templates work without an open conversation window — they are the
        correct approach for business-initiated contacts.
        Parameters are positional: [{"type":"text","text":"value"}, ...] mapped
        to {{1}}, {{2}}, ... in the approved template body.
        """
        return self._run_sync(
            self._async_send_meta_template(
                to_number, template_name, components, language_code
            )
        )

    async def _async_send_meta_template(
        self,
        to_number: str,
        template_name: str,
        components: list[dict[str, Any]] | None = None,
        language_code: str = "en",
    ) -> tuple[bool, str]:
        """Async implementation of Meta template send."""
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
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    url,
                    headers=self._meta_headers(),
                    content=json.dumps(payload),
                )
            data: dict[str, Any] = {}
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}

            log.info(
                "Meta template send response",
                status=resp.status_code,
                body=data,
                payload=payload,
            )

            if 200 <= resp.status_code < 300:
                return True, "sent"

            err = data.get("error", {})
            message = err.get("message") or data.get("raw") or "Unknown Meta error"
            code = err.get("code")
            error_data = err.get("error_data", {})
            details = error_data.get("details", "")
            log.error(
                "Meta template send FAILED",
                code=code,
                message=message,
                error_data=error_data,
                details=details,
                sent_payload=payload,
            )
            detail_suffix = f" | {details}" if details else ""
            return False, f"Meta HTTP {resp.status_code} Error ({code}): {message}{detail_suffix}"
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
        email_id: str | None = None,
    ) -> tuple[bool, str]:
        """Send a standard email alert template.

        Template body uses named parameters: email_sender, email_subject, email_summary.
        Button at index 0 carries the cancel payload.
        """
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "parameter_name": "email_sender", "text": _sanitize_template_param(sender)[:100]},
                    {"type": "text", "parameter_name": "email_subject", "text": _sanitize_template_param(subject)[:150]},
                    {"type": "text", "parameter_name": "email_summary", "text": _sanitize_template_param(summary)[:300]},
                ]
            },
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": 0,
                "parameters": [
                    {
                        "type": "payload",
                        "payload": f"cancel_reply_{email_id or 'test'}"
                    }
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
        """Send an auto-reply notification with a cancel button.

        FALLBACK: Since the 'auto_reply_alerts' template is currently 'In review'
        on Meta, we temporarily route this notification through the approved
        'email_alerts' template so you still receive notifications and can cancel replies.
        """
        fallback_summary = (
            f"[Auto-reply Draft] {reply_draft} "
            f"(You have {cancel_seconds}s to cancel)"
        )
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "parameter_name": "email_sender", "text": _sanitize_template_param(sender)[:100]},
                    {"type": "text", "parameter_name": "email_subject", "text": _sanitize_template_param(subject)[:150]},
                    {"type": "text", "parameter_name": "email_summary", "text": _sanitize_template_param(fallback_summary)[:300]},
                ]
            },
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": 0,
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
            template_name="email_alerts",
            components=components,
        )


    def _send_meta_text(self, to_number: str, text: str) -> tuple[bool, str]:
        """Send a free-form text message via Meta Cloud API.

        Only works inside a 24-hour conversation window (user must have messaged
        first). For business-initiated contacts, use send_alert_template instead.
        """
        return self._run_sync(self._async_send_meta_text(to_number, text))

    async def _async_send_meta_text(self, to_number: str, text: str) -> tuple[bool, str]:
        """Async implementation of free-form text send."""
        url = f"https://graph.facebook.com/{_META_API_VERSION}/{self.meta_phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number.lstrip("+"),
            "type": "text",
            "text": {"body": text},
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
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
