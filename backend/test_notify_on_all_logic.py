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
from tasks.celery_app import _process_gmail_webhook_async

class TestNotifyOnAllLogic(unittest.IsolatedAsyncioTestCase):
    @patch("tasks.celery_app.AsyncSessionLocal")
    @patch("tasks.celery_app.GmailConnector")
    @patch("tasks.celery_app.process_incoming_email")
    @patch("tasks.celery_app.notifier")
    async def test_gmail_webhook_notify_on_all_true(self, mock_notifier, mock_process_email, mock_connector_class, mock_session_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_db
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.execute = AsyncMock()
        
        # Make db.execute return no existing record (first call scalar_one_or_none returns None)
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_existing

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        account_id = uuid.uuid4()

        # Mock user with notify_on_all = True
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            whatsapp_number="+919999999999",
            whatsapp_verified=True,
            notify_on_all=True
        )
        # Mock account
        account = ConnectedAccount(
            id=account_id,
            user_id=user_id,
            tenant_id=tenant_id,
            provider="gmail"
        )

        async def mock_get(model, pk):
            if model == ConnectedAccount:
                return account
            if model == User:
                return user
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)

        # Mock connector
        mock_connector = MagicMock()
        mock_connector_class.return_value = mock_connector
        mock_connector.get_message.return_value = {}
        mock_connector.parse_message.return_value = {
            "date": None,
            "sender_email": "test@example.com",
            "sender_name": "Test Sender",
            "subject": "Hello",
            "body": "World",
            "provider_message_id": "msg123",
            "provider_thread_id": "thread123"
        }

        # Mock process_incoming_email to return score = 30 (routine/low priority)
        mock_process_email.return_value = (30, "Low score summary", None, "Keyword analysis")

        # Run webhook
        await _process_gmail_webhook_async(str(account_id), "msg123")

        # Assertions:
        # Since notify_on_all is True, it should trigger alert and notifier send_alert_template
        # even though score is 30 (which is < 80)
        self.assertEqual(mock_db.add.call_count, 1)
        added_record = mock_db.add.call_args[0][0]
        self.assertIsInstance(added_record, EmailRecord)
        self.assertEqual(added_record.status, "alerted")
        mock_notifier.send_alert_template.assert_called_once()

    @patch("tasks.celery_app.AsyncSessionLocal")
    @patch("tasks.celery_app.GmailConnector")
    @patch("tasks.celery_app.process_incoming_email")
    @patch("tasks.celery_app.notifier")
    async def test_gmail_webhook_notify_on_all_false_low_score(self, mock_notifier, mock_process_email, mock_connector_class, mock_session_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_db
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.execute = AsyncMock()
        
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_existing

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        account_id = uuid.uuid4()

        # Mock user with notify_on_all = False
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            whatsapp_number="+919999999999",
            whatsapp_verified=True,
            notify_on_all=False
        )
        account = ConnectedAccount(
            id=account_id,
            user_id=user_id,
            tenant_id=tenant_id,
            provider="gmail"
        )

        async def mock_get(model, pk):
            if model == ConnectedAccount:
                return account
            if model == User:
                return user
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)

        # Mock connector
        mock_connector = MagicMock()
        mock_connector_class.return_value = mock_connector
        mock_connector.get_message.return_value = {}
        mock_connector.parse_message.return_value = {
            "date": None,
            "sender_email": "test@example.com",
            "sender_name": "Test Sender",
            "subject": "Hello",
            "body": "World",
            "provider_message_id": "msg123",
            "provider_thread_id": "thread123"
        }

        # Mock process_incoming_email to return score = 30 (below 80)
        mock_process_email.return_value = (30, "Low score summary", None, "Keyword analysis")

        # Run webhook
        await _process_gmail_webhook_async(str(account_id), "msg123")

        # Assertions:
        # Since notify_on_all is False and score is 30, it should NOT trigger alert and status should be pending
        self.assertEqual(mock_db.add.call_count, 1)
        added_record = mock_db.add.call_args[0][0]
        self.assertIsInstance(added_record, EmailRecord)
        self.assertEqual(added_record.status, "pending")
        mock_notifier.send_alert_template.assert_not_called()

    @patch("tasks.celery_app.AsyncSessionLocal")
    @patch("tasks.celery_app.GmailConnector")
    @patch("tasks.celery_app.process_incoming_email")
    @patch("tasks.celery_app.notifier")
    async def test_gmail_webhook_notify_on_all_false_high_score(self, mock_notifier, mock_process_email, mock_connector_class, mock_session_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_db
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.execute = AsyncMock()
        
        mock_existing = MagicMock()
        mock_existing.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_existing

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        account_id = uuid.uuid4()

        # Mock user with notify_on_all = False
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            whatsapp_number="+919999999999",
            whatsapp_verified=True,
            notify_on_all=False
        )
        account = ConnectedAccount(
            id=account_id,
            user_id=user_id,
            tenant_id=tenant_id,
            provider="gmail"
        )

        async def mock_get(model, pk):
            if model == ConnectedAccount:
                return account
            if model == User:
                return user
            return None
        mock_db.get = AsyncMock(side_effect=mock_get)

        # Mock connector
        mock_connector = MagicMock()
        mock_connector_class.return_value = mock_connector
        mock_connector.get_message.return_value = {}
        mock_connector.parse_message.return_value = {
            "date": None,
            "sender_email": "test@example.com",
            "sender_name": "Test Sender",
            "subject": "Hello",
            "body": "World",
            "provider_message_id": "msg123",
            "provider_thread_id": "thread123"
        }

        # Mock process_incoming_email to return score = 85 (>= 80)
        mock_process_email.return_value = (85, "High score summary", None, "Keyword analysis")

        # Run webhook
        await _process_gmail_webhook_async(str(account_id), "msg123")

        # Assertions:
        # Since notify_on_all is False and score is 85, it should trigger alert and status should be alerted
        self.assertEqual(mock_db.add.call_count, 1)
        added_record = mock_db.add.call_args[0][0]
        self.assertIsInstance(added_record, EmailRecord)
        self.assertEqual(added_record.status, "alerted")
        mock_notifier.send_alert_template.assert_called_once()

if __name__ == "__main__":
    unittest.main()
