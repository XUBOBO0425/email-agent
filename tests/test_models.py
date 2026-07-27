import pytest
from datetime import datetime
from email_agent.memory.models import ProcessedEmail, Task, SkippedEmail, Report, Email


def test_email_dataclass():
    email = Email(
        message_id="<abc@163.com>",
        uid=123,
        sender_email="zhang@company.com",
        sender_name="张三",
        subject="Q3 预算",
        body="请审批",
        received_at=datetime(2026, 7, 27, 10, 0, 0),
    )
    assert email.message_id == "<abc@163.com>"
    assert email.sender_email == "zhang@company.com"


def test_processed_email_from_email():
    email = Email(
        message_id="<abc@163.com>",
        uid=123,
        sender_email="zhang@company.com",
        sender_name="张三",
        subject="Q3 预算",
        body="请审批",
        received_at=datetime(2026, 7, 27, 10, 0, 0),
    )
    processed = ProcessedEmail.from_email(
        email=email,
        category="work",
        priority="urgent",
        summary="Q3预算需审批",
        classification_reason="来自老板，含审批关键词",
    )
    assert processed.message_id == email.message_id
    assert processed.category == "work"
    assert processed.priority == "urgent"


def test_task_model():
    task = Task(
        content="周五前审批Q3预算",
        source_email_id="<abc@163.com>",
        due_date="2026-07-31",
    )
    assert task.status == "pending"
    assert task.due_date == "2026-07-31"


def test_skipped_email():
    skipped = SkippedEmail(
        message_id="<bad@163.com>",
        uid=456,
        sender_email="news@corp.com",
        subject="乱码邮件",
        reason="GBK decode error",
    )
    assert skipped.reason == "GBK decode error"


def test_report_model():
    report = Report(
        type="daily",
        period_start="2026-07-27",
        period_end="2026-07-27",
        content="今日共处理20封邮件...",
    )
    assert report.type == "daily"
