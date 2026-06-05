import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.email_record import EmailRecord
from models.user import User
from models.account import ConnectedAccount
from models.auto_reply import AutoReplyRule
from whatsapp.meta_webhook import process_whatsapp_message
from tasks.celery_app import _send_delayed_auto_reply_async

class TestWhatsAppCancelFlow(unittest.IsolatedAsyncioTestCase):
    @patch("whatsapp.meta_webhook.AsyncSessionLocal")
    @patch("whatsapp.meta_notifier.meta_notifier._send_text")
    async def test_webhook_cancel_updates_db(self, mock_send_text, mock_db_session_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_db_session_class.return_value.__aenter__.return_value = mock_db
        
        # Make db.commit awaitable
        mock_db.commit = AsyncMock()
        
        test_user_id = uuid.uuid4()
        test_tenant_id = uuid.uuid4()
        test_email_id = uuid.uuid4()
        
        # Mock user lookup
        mock_user = User(
            id=test_user_id,
            tenant_id=test_tenant_id,
            whatsapp_number="+919999999999",
            whatsapp_verified=True
        )
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user
        
        # Mock email lookup
        mock_email = EmailRecord(
            id=test_email_id,
            tenant_id=test_tenant_id,
            subject="Important business",
            sender_email="boss@company.com",
            status="alerted"
        )
        mock_email_result = MagicMock()
        mock_email_result.scalar_one_or_none.return_value = mock_email
        
        # db.execute call sequence
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [mock_user_result, mock_email_result]
        
        # Run function under test
        await process_whatsapp_message(
            from_number="+919999999999",
            message_text=None,
            button_id=f"cancel_reply_{test_email_id}"
        )
        
        # Assertions
        self.assertEqual(mock_email.status, "cancelled")
        mock_db.commit.assert_called_once()
        mock_send_text.assert_called_once_with(
            to_number="+919999999999",
            text="Auto-reply to 'Important business' has been cancelled."
        )

    @patch("tasks.celery_app.AsyncSessionLocal")
    async def test_delayed_task_skips_cancelled(self, mock_db_session_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_db_session_class.return_value.__aenter__.return_value = mock_db
        
        test_email_id = uuid.uuid4()
        
        # Mock email record that is cancelled
        mock_email = EmailRecord(
            id=test_email_id,
            status="cancelled",
            auto_reply_content="Hello there"
        )
        # Make db.get awaitable
        mock_db.get = AsyncMock(return_value=mock_email)
        mock_db.commit = AsyncMock()
        
        # Run delayed task async wrapper
        await _send_delayed_auto_reply_async(str(test_email_id))
        
        # Assertions: db.get called, but commit and sender logic skipped
        mock_db.get.assert_called_once_with(EmailRecord, test_email_id)
        mock_db.commit.assert_not_called()

if __name__ == "__main__":
    unittest.main()
