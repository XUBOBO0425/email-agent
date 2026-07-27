import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from email_agent.email.base import EmailAdapter
from email_agent.email.imap_ import IMAPAdapter


class TestIMAPAdapter:
    def test_adapter_is_abstract(self):
        with pytest.raises(TypeError):
            EmailAdapter()

    def test_imap_is_concrete(self):
        adapter = IMAPAdapter(
            server="imap.163.com",
            port=993,
            address="test@163.com",
            password="test",
        )
        assert isinstance(adapter, EmailAdapter)

    @patch("imaplib.IMAP4_SSL")
    def test_connect(self, mock_imap):
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter.connect()
        mock_imap.assert_called_once_with("imap.163.com", 993)
        mock_imap.return_value.login.assert_called_once_with("test@163.com", "test")

    @patch("imaplib.IMAP4_SSL")
    def test_search_unseen(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.search.return_value = ("OK", [b"1 2 3 4 5"])
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        uids = adapter.search_unseen()
        assert uids == ["1", "2", "3", "4", "5"]

    @patch("imaplib.IMAP4_SSL")
    def test_search_unseen_empty(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.search.return_value = ("OK", [b""])
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        uids = adapter.search_unseen()
        assert uids == []

    @patch("imaplib.IMAP4_SSL")
    def test_search_by_date(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.search.return_value = ("OK", [b"10 11 12"])
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        uids = adapter.search_by_date("2026-07-01", "2026-07-27")
        assert uids == ["10", "11", "12"]

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_header(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.fetch.return_value = (
            "OK",
            [(b"1 (UID 1)", b"Message-ID: <abc@163.com>\r\nSubject: =?UTF-8?B?5rWL6K+V?=")]
        )
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        msg_id = adapter.fetch_header("1", "Message-ID")
        assert msg_id == "<abc@163.com>"

    @patch("imaplib.IMAP4_SSL")
    def test_fetch_header_not_found(self, mock_imap):
        mock_conn = mock_imap.return_value
        mock_conn.fetch.return_value = (
            "OK",
            [(b"1 (UID 1)", b"Subject: Test")]
        )
        adapter = IMAPAdapter("imap.163.com", 993, "test@163.com", "test")
        adapter._conn = mock_conn
        result = adapter.fetch_header("1", "Message-ID")
        assert result is None
