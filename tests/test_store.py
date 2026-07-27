import pytest
import os
import tempfile
from datetime import datetime
from email_agent.memory.store import MemoryStore
from email_agent.memory.models import ProcessedEmail, Task, SkippedEmail, Report


@pytest.fixture
def store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = MemoryStore(path)
    s.init()
    yield s
    s.close()
    os.unlink(path)


def make_email(message_id="<abc@163.com>", sender="zhang@company.com",
               sender_name="张三", received=None):
    return ProcessedEmail(
        message_id=message_id,
        uid=1,
        sender_email=sender,
        sender_name=sender_name,
        subject="Test",
        body="Test body content",
        received_at=received or datetime(2026, 7, 27, 10, 0, 0),
        category="work",
        priority="urgent",
        summary="test summary",
        classification_reason="test reason",
    )


class TestEmailCRUD:
    def test_save_and_exists(self, store):
        email = make_email()
        assert not store.exists(email.message_id)
        store.save_email(email)
        assert store.exists(email.message_id)

    def test_save_duplicate_ignored(self, store):
        email = make_email()
        store.save_email(email)
        store.save_email(email)
        history = store.get_sender_history("zhang@company.com")
        assert len(history) == 1

    def test_get_sender_history_ordered(self, store):
        older = make_email("<older@163.com>", received=datetime(2026, 7, 20))
        newer = make_email("<newer@163.com>", received=datetime(2026, 7, 27))
        store.save_email(older)
        store.save_email(newer)
        history = store.get_sender_history("zhang@company.com")
        assert history[0].message_id == "<newer@163.com>"
        assert history[1].message_id == "<older@163.com>"

    def test_get_sender_history_limit(self, store):
        for i in range(15):
            store.save_email(make_email(f"<id{i}@163.com>"))
        history = store.get_sender_history("zhang@company.com")
        assert len(history) == 10

    def test_get_emails_in_range(self, store):
        in_range = make_email("<in@163.com>", received=datetime(2026, 7, 25))
        out_range = make_email("<out@163.com>", received=datetime(2026, 7, 20))
        store.save_email(in_range)
        store.save_email(out_range)
        results = store.get_emails_in_range("2026-07-24", "2026-07-28")
        assert len(results) == 1
        assert results[0].message_id == "<in@163.com>"


class TestTaskCRUD:
    def test_save_and_get_tasks(self, store):
        task = Task(content="审批预算", source_email_id="<abc@163.com>", due_date="2026-07-31")
        store.save_task(task)
        tasks = store.get_pending_tasks()
        assert len(tasks) == 1
        assert tasks[0].content == "审批预算"

    def test_mark_task_done(self, store):
        task = Task(content="审批预算", source_email_id="<abc@163.com>")
        store.save_task(task)
        tasks = store.get_pending_tasks()
        store.mark_task_done(tasks[0].id)
        assert len(store.get_pending_tasks()) == 0

    def test_get_tasks_by_email(self, store):
        store.save_task(Task(content="任务1", source_email_id="<abc@163.com>"))
        store.save_task(Task(content="任务2", source_email_id="<xyz@163.com>"))
        tasks = store.get_tasks_by_email("<abc@163.com>")
        assert len(tasks) == 1
        assert tasks[0].content == "任务1"


class TestSkippedEmails:
    def test_save_and_get_skipped(self, store):
        skipped = SkippedEmail(
            message_id="<bad@163.com>", uid=1,
            sender_email="n@c.com", subject="Bad",
            reason="decode error",
        )
        store.save_skipped(skipped)
        results = store.get_skipped_emails()
        assert len(results) == 1
        assert results[0].reason == "decode error"


class TestReportCRUD:
    def test_save_and_get_reports(self, store):
        report = Report(
            type="daily",
            period_start="2026-07-27",
            period_end="2026-07-27",
            content="处理了20封邮件",
        )
        store.save_report(report)
        results = store.get_reports("daily", limit=10)
        assert len(results) == 1
        assert "20封" in results[0].content
