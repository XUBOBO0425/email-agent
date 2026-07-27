from email_agent.agent.tools.registry import get_registry

CLASSIFY_DEFINITION = {
    "name": "classify_email",
    "description": "对邮件进行分类并标记优先级。调用后结果会自动保存。",
    "input_schema": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "邮件的Message-ID",
            },
            "category": {
                "type": "string",
                "description": "分类标签",
            },
            "priority": {
                "type": "string",
                "enum": ["urgent", "high", "normal", "low"],
                "description": "优先级",
            },
            "summary": {
                "type": "string",
                "description": "一句话中文摘要",
            },
            "reason": {
                "type": "string",
                "description": "分类依据",
            },
        },
        "required": ["message_id", "category", "priority", "summary", "reason"],
    },
}


def register(memory):
    """Register classify tool with given memory store."""

    def handler(message_id: str, category: str, priority: str,
                summary: str, reason: str) -> str:
        return (
            f"已分类: {category} | 优先级: {priority}\n"
            f"摘要: {summary}\n"
            f"依据: {reason}"
        )

    get_registry().register("classify_email", CLASSIFY_DEFINITION, handler)
