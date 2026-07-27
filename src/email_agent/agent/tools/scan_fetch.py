import logging
from email_agent.agent.tools.registry import get_registry

logger = logging.getLogger(__name__)

SEARCH_BY_DATE_DEFINITION = {
    "name": "search_by_date",
    "description": "按时间段拉取所有邮件（含已读）。对已存在于数据库的邮件复用已有分类。",
    "input_schema": {
        "type": "object",
        "properties": {
            "since": {
                "type": "string",
                "description": "起始日期 YYYY-MM-DD",
            },
            "before": {
                "type": "string",
                "description": "结束日期 YYYY-MM-DD",
            },
        },
        "required": ["since", "before"],
    },
}

GET_SENDER_HISTORY_DEFINITION = {
    "name": "get_sender_history",
    "description": "查询某发件人的历史邮件统计和最近邮件摘要。",
    "input_schema": {
        "type": "object",
        "properties": {
            "sender_email": {
                "type": "string",
                "description": "发件人邮箱地址",
            },
        },
        "required": ["sender_email"],
    },
}

GET_PENDING_TASKS_DEFINITION = {
    "name": "get_pending_tasks",
    "description": "获取当前所有未完成的待办事项列表。",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


def register(adapter, memory):
    """Register search_by_date and query tools."""

    def search_by_date_handler(since: str, before: str) -> str:
        try:
            uids = adapter.search_by_date(since, before)
            if not uids:
                return f"{since} ~ {before} 期间没有邮件。"

            emails_info = []
            new_count = 0
            cached_count = 0

            for uid in uids[:100]:  # cap at 100 for performance
                msg_id = adapter.fetch_header(uid, "Message-ID")
                subject = adapter.fetch_header(uid, "Subject") or "(无主题)"

                if msg_id and memory.exists(msg_id):
                    cached_count += 1
                    emails_info.append(f"[已缓存] {subject}")
                else:
                    new_count += 1
                    emails_info.append(f"[待处理] {subject}")

            return (
                f"{since} ~ {before}: 共 {len(uids)} 封 ({len(emails_info)} 显示)\n"
                f"已缓存: {cached_count}, 待处理: {new_count}\n\n" +
                "\n".join(emails_info)
            )
        except Exception as e:
            return f"搜索失败: {e}"

    def get_sender_history_handler(sender_email: str) -> str:
        history = memory.get_sender_history(sender_email)
        if not history:
            return f"未找到 {sender_email} 的历史邮件。"

        urgent_count = sum(1 for e in history if e.priority == "urgent")
        high_count = sum(1 for e in history if e.priority == "high")
        categories = set(e.category for e in history)

        lines = [
            f"【{sender_email} 历史】",
            f"近 {len(history)} 封邮件: urgent: {urgent_count}, high: {high_count}",
            f"涉及分类: {', '.join(categories)}",
            "",
            "最近邮件:",
        ]
        for e in history[:5]:
            lines.append(f"  [{e.priority}] {e.subject} ({e.received_at})")
        return "\n".join(lines)

    def get_pending_tasks_handler() -> str:
        tasks = memory.get_pending_tasks()
        if not tasks:
            return "当前没有待办事项。"

        lines = [f"当前 {len(tasks)} 个待办:"]
        for t in tasks:
            due = f" | 截止: {t.due_date}" if t.due_date else ""
            lines.append(f"  - {t.content}{due}")
        return "\n".join(lines)

    get_registry().register("search_by_date", SEARCH_BY_DATE_DEFINITION,
                            search_by_date_handler)
    get_registry().register("get_sender_history", GET_SENDER_HISTORY_DEFINITION,
                            get_sender_history_handler)
    get_registry().register("get_pending_tasks", GET_PENDING_TASKS_DEFINITION,
                            get_pending_tasks_handler)
