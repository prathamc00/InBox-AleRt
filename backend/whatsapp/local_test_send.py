"""Local test harness to build and print WhatsApp template payloads
without making network calls."""

import sys
import os
import json

# Ensure backend is on path (so 'whatsapp' package imports work)
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(HERE)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from whatsapp.meta_notifier import meta_notifier


def main():
    to_number = "+15555550123"

    # Build alert payload
    alert_components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "parameter_name": "email_body", "text": "Score: 85 From: sam.ko@example.com Subject: Urgent: Review Q3 Plan Summary: AI: Sam, I will look into this as soon as possible Reason: Matched rule: High-priority sender"}
            ]
        }
    ]

    alert_payload = meta_notifier.build_template_payload(
        to_number=to_number,
        template_name="email_alerts",
        components=alert_components,
    )

    print("\n=== ALERT PAYLOAD ===")
    print(json.dumps(alert_payload, indent=2))

    # Build auto-reply payload
    auto_components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "parameter_name": "email_body", "text": "Score: 90 From: sam.ko@example.com Subject: Urgent: Review Q3 Plan Draft: Hi Sam, I will look into this as soon as possible. You have 60 seconds to cancel."}
            ]
        },
        {
            "type": "button",
            "sub_type": "quick_reply",
            "index": 0,
            "parameters": [{"type": "payload", "payload": "confirm_reply_test"}],
        },
        {
            "type": "button",
            "sub_type": "quick_reply",
            "index": 1,
            "parameters": [{"type": "payload", "payload": "cancel_reply_test"}],
        },
    ]

    auto_payload = meta_notifier.build_template_payload(
        to_number=to_number,
        template_name="auto_reply_alerts",
        components=auto_components,
    )

    print("\n=== AUTO-REPLY PAYLOAD ===")
    print(json.dumps(auto_payload, indent=2))


if __name__ == "__main__":
    main()
