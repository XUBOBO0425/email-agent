import pytest
from unittest.mock import MagicMock
from datetime import datetime
from email_agent.agent.core import Agent, ProcessResult
from email_agent.agent.tools.registry import ToolRegistry
from email_agent.llm.client import ClaudeResponse, ToolUse
from email_agent.memory.models import Email


class MockLLM:
    """Controllable LLM for testing agent logic."""
    def __init__(self):
        self.responses = []
        self.calls = []

    def add_response(self, response: ClaudeResponse):
        self.responses.append(response)

    def send(self, system_prompt, messages, tools=None, max_retries=3):
        self.calls.append({"system": system_prompt, "messages": messages, "tools": tools})
        if self.responses:
            return self.responses.pop(0)
        return ClaudeResponse(text="done", stop_reason="end_turn")


@pytest.fixture
def mock_llm():
    return MockLLM()


@pytest.fixture
def sample_email():
    return Email(
        message_id="<test@163.com>",
        uid=1,
        sender_email="boss@company.com",
        sender_name="老板",
        subject="紧急会议",
        body="今天下午3点开会讨论Q3预算。",
        received_at=datetime(2026, 7, 27, 10, 0, 0),
    )


@pytest.fixture
def agent(mock_llm):
    registry = ToolRegistry()
    executed = {}

    registry.register("test_tool", {
        "name": "test_tool",
        "description": "A test tool",
        "input_schema": {"type": "object", "properties": {"arg": {"type": "string"}}, "required": ["arg"]},
    }, lambda arg: executed.update({"arg": arg}) or f"executed: {arg}")

    memory = MagicMock()
    memory.get_sender_history.return_value = []
    memory.get_pending_tasks.return_value = []

    return Agent(llm=mock_llm, registry=registry, memory=memory, max_turns=3)


class TestAgentLoop:
    def test_stops_on_text_response(self, agent, mock_llm, sample_email):
        """Agent should stop when Claude returns text without tool calls."""
        mock_llm.add_response(ClaudeResponse(
            text="已完成处理", stop_reason="end_turn", tool_uses=[]
        ))
        result = agent.process_email(sample_email)
        assert result.turns_used == 1
        assert result.force_stopped is False

    def test_executes_tool_and_continues(self, agent, mock_llm, sample_email):
        """Agent should execute tool call and send result back to Claude."""
        mock_llm.add_response(ClaudeResponse(
            text="",
            stop_reason="tool_use",
            tool_uses=[ToolUse(id="call_1", name="test_tool", input={"arg": "value1"})],
        ))
        mock_llm.add_response(ClaudeResponse(
            text="处理完成", stop_reason="end_turn", tool_uses=[]
        ))
        result = agent.process_email(sample_email)
        assert result.turns_used == 2
        assert len(result.tool_results) == 1

    def test_force_stop_at_max_turns(self, agent, mock_llm, sample_email):
        """Agent should force stop when max_turns is reached."""
        for _ in range(5):
            mock_llm.add_response(ClaudeResponse(
                text="",
                stop_reason="tool_use",
                tool_uses=[ToolUse(id="call_1", name="test_tool", input={"arg": "x"})],
            ))
        result = agent.process_email(sample_email)
        assert result.force_stopped is True
        assert result.turns_used == 3  # max_turns

    def test_unknown_tool_handled(self, agent, mock_llm, sample_email):
        """Agent should handle unknown tool gracefully."""
        mock_llm.add_response(ClaudeResponse(
            text="",
            stop_reason="tool_use",
            tool_uses=[ToolUse(id="call_1", name="nonexistent", input={})],
        ))
        mock_llm.add_response(ClaudeResponse(
            text="done", stop_reason="end_turn", tool_uses=[]
        ))
        result = agent.process_email(sample_email)
        assert result.turns_used == 2
        assert "unknown" in str(result.tool_results[0]).lower()

    def test_context_includes_sender_history(self, agent, mock_llm, sample_email):
        """Agent should include sender history in the context sent to Claude."""
        mock_llm.add_response(ClaudeResponse(
            text="done", stop_reason="end_turn", tool_uses=[]
        ))
        agent.process_email(sample_email)
        call = mock_llm.calls[0]
        messages_text = str(call["messages"])
        assert sample_email.subject in messages_text
        assert sample_email.sender_email in messages_text
