"""Tests for DeepSeek client format conversion functions."""
import json
from email_agent.llm.deepseek_client import _build_openai_messages, _convert_tools


class TestMessageConversion:
    def test_simple_user_message(self):
        """Plain text message passes through unchanged (plus system prompt)."""
        messages = [{"role": "user", "content": "Hello"}]
        result = _build_openai_messages("You are helpful.", messages)
        assert result == [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]

    def test_no_system_prompt(self):
        """Empty system prompt produces no system message."""
        messages = [{"role": "user", "content": "Hi"}]
        result = _build_openai_messages("", messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_assistant_with_tool_use(self):
        """Assistant tool_use blocks → OpenAI tool_calls format."""
        messages = [{
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Let me classify this."},
                {"type": "tool_use", "id": "call_1", "name": "classify_email",
                 "input": {"category": "work", "priority": "urgent"}},
            ],
        }]
        result = _build_openai_messages("", messages)
        assert len(result) == 1
        msg = result[0]
        assert msg["role"] == "assistant"
        assert "Let me classify" in msg["content"]
        assert len(msg["tool_calls"]) == 1
        tc = msg["tool_calls"][0]
        assert tc["id"] == "call_1"
        assert tc["function"]["name"] == "classify_email"
        assert json.loads(tc["function"]["arguments"]) == {"category": "work", "priority": "urgent"}

    def test_user_with_tool_results(self):
        """User tool_result blocks → OpenAI 'tool' role messages."""
        messages = [{
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1",
                 "content": "已分类: work"},
                {"type": "tool_result", "tool_use_id": "call_2",
                 "content": "提取了 1 个待办"},
            ],
        }]
        result = _build_openai_messages("", messages)
        assert len(result) == 2
        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "call_1"
        assert result[1]["role"] == "tool"
        assert result[1]["tool_call_id"] == "call_2"

    def test_multi_turn_conversation(self):
        """Full agent loop conversation: init → tool call → tool result."""
        messages = [
            {"role": "user", "content": "请处理这封邮件"},
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "c1", "name": "classify_email",
                 "input": {"priority": "normal"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "c1",
                 "content": "已分类: normal"},
            ]},
        ]
        result = _build_openai_messages("system prompt", messages)
        assert len(result) == 4
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"
        assert "tool_calls" in result[2]
        assert result[3]["role"] == "tool"


class TestToolConversion:
    def test_convert_classify_tool(self):
        anthropic_tool = {
            "name": "classify_email",
            "description": "分类并标记优先级",
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "priority": {"type": "string", "enum": ["urgent", "high", "normal", "low"]},
                },
                "required": ["category", "priority"],
            },
        }
        result = _convert_tools([anthropic_tool])
        assert len(result) == 1
        assert result[0]["type"] == "function"
        func = result[0]["function"]
        assert func["name"] == "classify_email"
        assert "required" in func["parameters"]
        assert func["parameters"]["required"] == ["category", "priority"]

    def test_convert_multiple_tools(self):
        tools = [
            {"name": "tool_a", "description": "A", "input_schema": {}},
            {"name": "tool_b", "description": "B", "input_schema": {}},
        ]
        result = _convert_tools(tools)
        assert len(result) == 2
        assert result[0]["function"]["name"] == "tool_a"
        assert result[1]["function"]["name"] == "tool_b"

