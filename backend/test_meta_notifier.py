import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["WHATSAPP_ACCESS_TOKEN"] = "test_token"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "test_phone_id"

# Make sure we can import the module correctly
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from whatsapp.meta_notifier import MetaNotifier

class TestMetaNotifier(unittest.TestCase):
    def setUp(self):
        # Temporarily override settings if they exist
        from core.config import settings
        settings.WHATSAPP_ACCESS_TOKEN = "test_token"
        settings.WHATSAPP_PHONE_NUMBER_ID = "test_phone_id"
        self.notifier = MetaNotifier()

    def test_diagnostics_configured(self):
        diag = self.notifier.diagnostics()
        self.assertEqual(diag["provider"], "meta")
        self.assertTrue(diag["meta_configured"])
        self.assertTrue(diag["meta_phone_number_id_present"])
        self.assertTrue(diag["meta_access_token_present"])
        self.assertNotIn("twilio_configured", diag)
        self.assertNotIn("twilio_from_present", diag)

    @patch("httpx.Client")
    def test_send_test_message_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        ok, result = self.notifier.send_test_message_result("+1234567890")
        self.assertTrue(ok)
        self.assertEqual(result, "sent")

    @patch("httpx.Client")
    def test_send_test_message_failure(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Invalid token", "code": 190}}
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        ok, result = self.notifier.send_test_message_result("+1234567890")
        self.assertFalse(ok)
        self.assertIn("Error (190): Invalid token", result)

    @patch("httpx.Client")
    def test_send_alert(self, mock_client_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        ok, result = self.notifier.send_alert(
            to_number="+1234567890",
            sender="sender@example.com",
            subject="Test Subject",
            summary="Test Summary",
            score=95,
            email_id="12345"
        )
        self.assertTrue(ok)
        self.assertEqual(result, "sent")

if __name__ == "__main__":
    unittest.main()
