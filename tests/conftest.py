import pytest
from datetime import datetime
from email_agent.memory.models import Email, ProcessedEmail, Task


@pytest.fixture
def sample_email():
    return Email(
        message_id="<test123@163.com>",
        uid=1,
        sender_email="zhang@company.com",
        sender_name="张三",
        subject="Q3 预算审批需要你的反馈",
        body="请在本周五之前审批Q3预算方案，详见附件。",
        received_at=datetime(2026, 7, 27, 10, 0, 0),
    )


@pytest.fixture
def sample_emails():
    return [
        Email(
            message_id=f"<test{i}@163.com>",
            uid=i,
            sender_email=f"sender{i}@company.com",
            sender_name=f"发件人{i}",
            subject=f"测试邮件{i}",
            body=f"这是第{i}封测试邮件的内容。",
            received_at=datetime(2026, 7, 27, 10, i, 0),
        )
        for i in range(5)
    ]
