import httpx
from core.config import settings
import structlog

log = structlog.get_logger()

class WhatsAppNotifier:
    def __init__(self):
        self.sid = settings.TWILIO_ACCOUNT_SID
        self.token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_FROM
        self.auth = (self.sid, self.token)
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json"

    def _send_message_result(self, to_number: str, payload: dict) -> tuple[bool, str]:
        """Helper to send the HTTP request to Twilio API."""
        if not self.sid or not self.token or not self.from_number:
            log.warning("Twilio credentials missing. WhatsApp alert skipped.")
            return False, "Twilio credentials are missing."

        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        payload["From"] = self.from_number
        payload["To"] = to_number

        try:
            # Twilio API uses standard form-encoded data, NOT json
            response = httpx.post(self.base_url, auth=self.auth, data=payload, timeout=10.0)
            if response.status_code >= 400:
                try:
                    data = response.json()
                    detail = f"Twilio error {data.get('code', response.status_code)}: {data.get('message', 'Unknown error')}"
                except Exception:
                    detail = f"Twilio error {response.status_code}: {response.text[:300]}"
                log.error("Failed to send WhatsApp message", status_code=response.status_code, detail=detail)
                return False, detail

            log.info("WhatsApp message sent", to=to_number)
            return True, "Message sent"
        except Exception as exc:
            log.error("Failed to send WhatsApp message", error=str(exc))
            return False, str(exc)

    def _send_message(self, to_number: str, payload: dict) -> bool:
        ok, _ = self._send_message_result(to_number, payload)
        return ok

    def send_alert(self, to_number: str, sender: str, subject: str, summary: str, score: int, email_id: str):
        """
        Sends an interactive WhatsApp alert with quick-reply buttons.
        Twilio doesn't support dynamic quick replies via standard API without templates,
        but for Sandbox testing, we can format a nice text message and ask them to reply.
        (For production, we would use Content Templates for actual UI buttons).
        """
        message_body = (
            f"🚨 *Important Email Alert (Score: {score})*\n\n"
            f"👤 *From:* {sender}\n"
            f"📌 *Subject:* {subject}\n\n"
            f"📝 *AI Summary:*\n{summary}\n\n"
            f"Reply with exactly:\n"
            f"1️⃣ to send: 'Thanks, received.'\n"
            f"2️⃣ to send: 'Will review this today.'\n"
            f"3️⃣ to Snooze\n"
            f"(ID: {email_id})"
        )

        payload = {"Body": message_body}
        return self._send_message(to_number, payload)

    def send_auto_reply_notification(self, to_number: str, sender: str, summary: str, thread_id: str, subject: str = "", original_summary: str = ""):
        """
        Notifies the user that the AI has autonomously replied to an email.
        """
        message_body = (
            f"🤖 *AI Auto-Replied*\n\n"
            f"👤 *From:* {sender}\n"
            f"📌 *Subject:* {subject}\n\n"
            f"📝 *AI Summary:*\n{original_summary}\n\n"
            f"� *What I replied:*\n{summary}\n\n"
            f"If this was a mistake, reply 'CANCEL {thread_id}' within 60 seconds."
        )

        payload = {"Body": message_body}
        return self._send_message(to_number, payload)

    def send_test_message(self, to_number: str) -> bool:
        """Send a short connectivity test message to confirm WhatsApp delivery."""
        message_body = (
            "✅ InboxAlert WhatsApp connected successfully. "
            "You will now receive high-priority email alerts here."
        )
        return self._send_message(to_number, {"Body": message_body})

    def send_test_message_result(self, to_number: str) -> tuple[bool, str]:
        """Send a test message and return provider-level failure details."""
        message_body = (
            "✅ InboxAlert WhatsApp connected successfully. "
            "You will now receive high-priority email alerts here."
        )
        return self._send_message_result(to_number, {"Body": message_body})

    def list_recent_deliveries(
        self,
        to_number: str,
        limit: int = 10,
    ) -> tuple[bool, str, list[dict]]:
        """Return recent WhatsApp delivery statuses for a recipient number."""
        if not self.sid or not self.token:
            return False, "Twilio credentials are missing.", []

        to_value = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        try:
            response = httpx.get(
                self.base_url,
                auth=self.auth,
                params={"To": to_value, "PageSize": max(1, min(limit, 20))},
                timeout=10.0,
            )
            if response.status_code >= 400:
                try:
                    data = response.json()
                    detail = f"Twilio error {data.get('code', response.status_code)}: {data.get('message', 'Unknown error')}"
                except Exception:
                    detail = f"Twilio error {response.status_code}: {response.text[:300]}"
                return False, detail, []

            messages = response.json().get("messages", [])
            deliveries: list[dict] = []
            for m in messages:
                if not str(m.get("to", "")).startswith("whatsapp:"):
                    continue
                deliveries.append(
                    {
                        "sid": m.get("sid"),
                        "to": m.get("to"),
                        "from": m.get("from"),
                        "status": m.get("status"),
                        "error_code": m.get("error_code"),
                        "error_message": m.get("error_message"),
                        "date_sent": m.get("date_sent"),
                    }
                )
            return True, "ok", deliveries
        except Exception as exc:
            return False, str(exc), []

notifier = WhatsAppNotifier()
