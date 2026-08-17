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

    # Build alert payload formatted text
    sender = "submissions@formsubmit.co"
    subject = "Action Required: Activate FormSubmit on https://prathmeshai.vercel.app/"
    summary = "This email from FormSubmit requires you to activate a form on https://prathmeshai.vercel.app/ by clicking the 'Activate Form' link."
    reason = "Rule: Keyword analysis"
    score = 100

    combined_lines = [
        f"*Score:* {score}/100",
        f"*From:* {sender}",
        f"*Subject:* {subject}",
        f"\n*Summary:*\n{summary}",
        f"\n*Reason:* {reason}",
    ]
    formatted_alert_text = "\n".join(combined_lines)

    alert_components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "parameter_name": "email_body", "text": formatted_alert_text}
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
