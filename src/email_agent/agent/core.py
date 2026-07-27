# src/email_agent/agent/core.py
import logging
from dataclasses import dataclass, field
from email_agent.memory.models import Email, ProcessedEmail, SkippedEmail
from email_agent.prompts.system import build_system_prompt, build_classify_context
from email_agent.agent.tools.registry import ToolRegistry
from email_agent.llm.client import ClaudeClient, ClaudeResponse, ToolUse

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    email_id: str
    tool_results: list[str] = field(default_factory=list)
    turns_used: int = 0
    force_stopped: bool = False
    classification: dict | None = None


class Agent:
    def __init__(self, llm, registry: ToolRegistry,
                 memory, profile: str = "worker", max_turns: int = 5):
        self.llm = llm
        self.registry = registry
        self.memory = memory
        self.profile = profile
        self.max_turns = max_turns

    def process_email(self, email: Email) -> ProcessResult:
        """Process a single email through the agent loop."""
        result = ProcessResult(email_id=email.message_id)

        sender_history = self._format_sender_history(email.sender_email)
        pending_tasks = self._format_pending_tasks()

        email_info = (
            f"UID: {email.uid}\n"
            f"Message-ID: {email.message_id}\n"
            f"发件人: {email.sender_name} <{email.sender_email}>\n"
            f"主题: {email.subject}\n"
            f"时间: {email.received_at}\n"
            f"正文:\n{email.body}"
        )

        context = build_classify_context(email_info, sender_history, pending_tasks)
        system_prompt = build_system_prompt(self.profile)

        messages = [{"role": "user", "content": context}]

        for turn in range(self.max_turns):
            response = self.llm.send(
                system_prompt=system_prompt,
                messages=messages,
                tools=self.registry.get_definitions(),
            )

            if response.stop_reason != "tool_use":
                result.turns_used = turn + 1
                break

            tool_results_text = []
            for tool_use in response.tool_uses:
                tool_result = self.registry.execute(tool_use.name, tool_use.input)
                result.tool_results.append(tool_result)
                tool_results_text.append(
                    f"[{tool_use.name}] {tool_result}"
                )

                if tool_use.name == "classify_email":
                    result.classification = tool_use.input

            tool_result_content = []
            for i, tu in enumerate(response.tool_uses):
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result.tool_results[i],
                })

            messages.append({"role": "assistant", "content": [
                *[{"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input}
                  for tu in response.tool_uses],
            ]})
            messages.append({"role": "user", "content": tool_result_content})

        else:
            result.force_stopped = True
            result.turns_used = self.max_turns
            logger.warning("Email %s 达到 %d 轮上限，强制终止",
                           email.message_id, self.max_turns)

        return result

    def process_emails(self, emails: list[Email]) -> list[ProcessResult]:
        """Process multiple emails sequentially."""
        results = []
        for email in emails:
            try:
                result = self.process_email(email)
                results.append(result)
            except Exception as e:
                logger.warning("跳过邮件 %s: %s", email.message_id, e)
                self.memory.save_skipped(SkippedEmail(
                    message_id=email.message_id,
                    uid=email.uid,
                    sender_email=email.sender_email,
                    subject=email.subject,
                    reason=f"agent_failed: {e}",
                ))
        return results

    def generate_report_content(self, report_type: str, period_start: str,
                                period_end: str) -> str:
        """Generate a report using Claude."""
        from email_agent.prompts.system import build_report_context

        emails = self.memory.get_emails_in_range(period_start, period_end)
        tasks = self.memory.get_pending_tasks()

        email_data = self._format_email_list(emails)
        task_data = self._format_task_list(tasks)

        context = build_report_context(report_type, period_start, period_end,
                                       email_data, task_data)
        system_prompt = build_system_prompt(self.profile)

        response = self.llm.send(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": context}],
            tools=[],
        )
        return response.text

    def detect_profile(self, metadata: str) -> dict:
        """Detect user profile from email metadata."""
        from email_agent.prompts.system import build_profile_detection_context
        import json

        context = build_profile_detection_context(metadata)
        response = self.llm.send(
            system_prompt="你是一个分析用户邮件模式的助手。返回JSON格式的分析结果。",
            messages=[{"role": "user", "content": context}],
            tools=[],
        )
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "profile": "worker",
                "evidence": ["无法解析Claude的响应，使用默认角色"],
                "confidence": "low",
            }

    def _format_sender_history(self, sender_email: str) -> str:
        history = self.memory.get_sender_history(sender_email)
        if not history:
            return "（无历史记录）"

        urgent = sum(1 for e in history if e.priority == "urgent")
        high = sum(1 for e in history if e.priority == "high")
        lines = [
            f"近 7 天发了 {len(history)} 封邮件:",
            f"  urgent: {urgent} | high: {high}",
            "",
            "最近邮件:",
        ]
        for e in history[:10]:
            lines.append(f"  [{e.priority}] {e.subject} ({e.received_at})")
        return "\n".join(lines)

    def _format_pending_tasks(self) -> str:
        tasks = self.memory.get_pending_tasks()
        if not tasks:
            return "（无待办）"
        lines = [f"当前 {len(tasks)} 个待办:"]
        for t in tasks:
            due = f" | 截止: {t.due_date}" if t.due_date else ""
            lines.append(f"  - {t.content}{due}")
        return "\n".join(lines)

    def _format_email_list(self, emails: list) -> str:
        if not emails:
            return "（无邮件数据）"
        lines = []
        for e in emails:
            lines.append(
                f"[{e.priority}] {e.sender_name} <{e.sender_email}>\n"
                f"  主题: {e.subject}\n"
                f"  分类: {e.category} | 时间: {e.received_at}\n"
                f"  摘要: {e.summary}"
            )
        return "\n\n".join(lines)

    def _format_task_list(self, tasks: list) -> str:
        if not tasks:
            return "（无待办事项）"
        lines = []
        for t in tasks:
            due = f" | 截止: {t.due_date}" if t.due_date else ""
            lines.append(f"- [{t.status}] {t.content}{due}")
        return "\n".join(lines)
