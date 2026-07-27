import json
from email_agent.agent.tools.registry import get_registry

EXTRACT_DEFINITION = {
    "name": "extract_todos",
    "description": "从邮件中提取待办事项。每个待办包含内容和可选的截止日期。",
    "input_schema": {
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "邮件的Message-ID",
            },
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "待办内容（中文）",
                        },
                        "due_date": {
                            "type": "string",
                            "description": "截止日期 YYYY-MM-DD，无则填null",
                        },
                        "source_line": {
                            "type": "string",
                            "description": "邮件中暗示此任务的原文",
                        },
                    },
                    "required": ["content", "due_date", "source_line"],
                },
                "description": "提取的待办事项列表",
            },
        },
        "required": ["message_id", "todos"],
    },
}


def register(memory):
    """Register extract_todos tool."""

    def handler(message_id: str, todos: list[dict]) -> str:
        from email_agent.memory.models import Task

        count = 0
        for todo in todos:
            task = Task(
                content=todo["content"],
                source_email_id=message_id,
                due_date=todo.get("due_date") if todo.get("due_date") and todo["due_date"] != "null" else None,
            )
            memory.save_task(task)
            count += 1

        return f"已从邮件提取 {count} 个待办事项"

    get_registry().register("extract_todos", EXTRACT_DEFINITION, handler)
