import logging
from email_agent.agent.tools.registry import get_registry

logger = logging.getLogger(__name__)

FETCH_DEFINITION = {
    "name": "fetch_unread_emails",
    "description": "从IMAP服务器拉取所有未读邮件，自动基于Message-ID去重。返回新邮件的发件人、主题和正文摘要。",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


def register(adapter, memory):
    """Register the fetch tool with given adapter and memory store."""

    def handler() -> str:
        try:
            uids = adapter.search_unseen()
            if not uids:
                return "没有未读邮件。"

            new_emails = []
            for uid in uids:
                try:
                    msg_id = adapter.fetch_header(uid, "Message-ID")
                    if msg_id and memory.exists(msg_id):
                        continue
                    email = adapter.fetch_full(uid)
                    new_emails.append({
                        "uid": uid,
                        "message_id": email.message_id,
                        "sender": f"{email.sender_name} <{email.sender_email}>",
                        "subject": email.subject,
                        "body_preview": email.body[:300],
                        "received_at": email.received_at.isoformat(),
                    })
                except Exception as e:
                    logger.warning("跳过邮件 UID %s: %s", uid, e)

            if not new_emails:
                return "所有未读邮件都已处理过。"

            return _format_fetch_result(new_emails)
        except Exception as e:
            return f"拉取邮件失败: {e}"

    get_registry().register("fetch_unread_emails", FETCH_DEFINITION, handler)


def _format_fetch_result(emails: list[dict]) -> str:
    lines = [f"拉取到 {len(emails)} 封新邮件:\n"]
    for i, em in enumerate(emails, 1):
        lines.append(
            f"{i}. [{em['uid']}] {em['sender']}\n"
            f"   主题: {em['subject']}\n"
            f"   时间: {em['received_at']}\n"
            f"   预览: {em['body_preview']}...\n"
        )
    return "\n".join(lines)
