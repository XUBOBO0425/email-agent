from email_agent.agent.tools.registry import get_registry

REPORT_DEFINITION = {
    "name": "generate_report",
    "description": "生成邮件报告（日报、周报或时间段报告）。生成的报告会自动保存到数据库。",
    "input_schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["daily", "weekly", "scan"],
                "description": "报告类型",
            },
            "period_start": {
                "type": "string",
                "description": "起始日期 YYYY-MM-DD",
            },
            "period_end": {
                "type": "string",
                "description": "结束日期 YYYY-MM-DD",
            },
            "content": {
                "type": "string",
                "description": "报告正文（Markdown格式，中文）",
            },
        },
        "required": ["type", "period_start", "period_end", "content"],
    },
}


def register(memory):
    """Register generate_report tool."""

    def handler(type: str, period_start: str, period_end: str, content: str) -> str:
        from email_agent.memory.models import Report

        report = Report(
            type=type,
            period_start=period_start,
            period_end=period_end,
            content=content,
        )
        memory.save_report(report)
        return f"报告已保存 ({type}, {period_start} ~ {period_end})"

    get_registry().register("generate_report", REPORT_DEFINITION, handler)
