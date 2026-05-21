"""
WhatsApp Business API integration using Meta Cloud API.
Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import httpx
import structlog
from core.config import settings

log = structlog.get_logger()


class MetaWhatsAppNotifier:
    """
    WhatsApp Business Cloud API client.
    Supports text messages, templates, interactive buttons, and media.
    """
    
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.business_account_id = settings.WHATSAPP_BUSINESS_ACCOUNT_ID
        self.base_url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"
    
    def _send_request(self, payload: dict) -> tuple[bool, str, dict]:
        """Send message via WhatsApp Cloud API."""
        if not self.access_token or not self.phone_number_id:
            log.warning("WhatsApp credentials missing")
            return False, "WhatsApp credentials are missing", {}
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            response = httpx.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=15.0
            )
            
            data = response.json()
            
            if response.status_code >= 400:
                error_msg = data.get("error", {}).get("message", "Unknown error")
                error_code = data.get("error", {}).get("code", response.status_code)
                log.error(
                    "WhatsApp API error",
                    status=response.status_code,
                    code=error_code,
                    message=error_msg
                )
                return False, f"Error {error_code}: {error_msg}", data
            
            message_id = data.get("messages", [{}])[0].get("id")
            log.info("WhatsApp message sent", message_id=message_id)
            return True, "Message sent", data
            
        except Exception as exc:
            log.error("Failed to send WhatsApp message", error=str(exc))
            return False, str(exc), {}
    
    def send_text_message(self, to_number: str, body: str) -> bool:
        """Send a simple text message."""
        # Remove any prefixes and ensure E.164 format
        to_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"body": body}
        }
        
        ok, _, _ = self._send_request(payload)
        return ok
    
    def send_alert_with_buttons(
        self,
        to_number: str,
        sender: str,
        subject: str,
        summary: str,
        score: int,
        email_id: str
    ) -> bool:
        """
        Send an interactive alert with quick reply buttons.
        Uses WhatsApp's interactive message format.
        """
        to_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
        
        body_text = (
            f"🚨 *Important Email Alert (Score: {score})*\n\n"
            f"👤 *From:* {sender}\n"
            f"📌 *Subject:* {subject}\n\n"
            f"📝 *AI Summary:*\n{summary}"
        )
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text[:1024]},  # Max 1024 chars
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"reply_1_{email_id}",
                                "title": "Thanks, received"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"reply_2_{email_id}",
                                "title": "Will review today"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"snooze_{email_id}",
                                "title": "Snooze"
                            }
                        }
                    ]
                }
            }
        }
        
        ok, _, _ = self._send_request(payload)
        return ok
    
    def send_auto_reply_notification(
        self,
        to_number: str,
        sender: str,
        summary: str,
        thread_id: str,
        subject: str = "",
        original_summary: str = ""
    ) -> bool:
        """
        Notify user that AI auto-replied to an email.
        Tries to send detailed free-form text first (requires active 24-hour window).
        If that fails, falls back to the pre-approved hello_world template to ensure delivery.
        """
        to_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
        
        body_text = (
            f"🤖 *AI Auto-Replied*\n\n"
            f"👤 *From:* {sender}\n"
            f"📌 *Subject:* {subject}\n\n"
            f"📝 *Original:*\n{original_summary[:200]}\n\n"
            f"💬 *My Reply:*\n{summary[:200]}\n\n"
            f"Reply CANCEL within 60s to undo."
        )
        
        ok = self.send_text_message(to_number, body_text)
        if ok:
            return True
            
        log.info("Auto-reply custom text message failed, falling back to template")
        ok, _, _ = self._send_request({
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {"name": "hello_world", "language": {"code": "en"}}
        })
        return ok
    
    def send_template_message(
        self,
        to_number: str,
        template_name: str,
        language_code: str = "en",
        parameters: list[str] = None
    ) -> bool:
        """
        Send a pre-approved message template.
        Templates must be created and approved in Meta Business Manager.
        """
        to_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
        
        components = []
        if parameters:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in parameters]
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components
            }
        }
        
        ok, _, _ = self._send_request(payload)
        return ok
    
    def send_test_message(self, to_number: str) -> bool:
        """Send a test message using hello_world template."""
        return self.send_template_message(to_number, "hello_world", "en")

    def send_test_message_result(self, to_number: str) -> tuple[bool, str]:
        """Send test message and return detailed result."""
        to_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
        ok, msg, _ = self._send_request({
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {"name": "hello_world", "language": {"code": "en"}}
        })
        return ok, msg

    def send_alert(self, to_number: str, sender: str, subject: str, summary: str, score: int, email_id: str) -> bool:
        """
        Send alert.
        Tries to send an interactive alert with buttons first (requires active 24-hour window).
        If that fails, falls back to the pre-approved hello_world template to guarantee delivery.
        """
        to_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
        
        # Try sending the interactive alert first
        ok = self.send_alert_with_buttons(
            to_number=to_number,
            sender=sender,
            subject=subject,
            summary=summary,
            score=score,
            email_id=email_id
        )
        if ok:
            return True
            
        # Fallback to the hello_world template if interactive fails (e.g., outside 24h window)
        log.info("Interactive alert failed, falling back to template message")
        ok, _, _ = self._send_request({
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {"name": "hello_world", "language": {"code": "en"}}
        })
        return ok
    
    def mark_message_as_read(self, message_id: str) -> bool:
        """Mark an incoming message as read."""
        if not self.access_token or not self.phone_number_id:
            return False
        
        url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
            return response.status_code < 400
        except Exception as exc:
            log.error("Failed to mark message as read", error=str(exc))
            return False


# Singleton instance
meta_notifier = MetaWhatsAppNotifier()
