import json
import time
import logging
from typing import Optional

from openai import OpenAI, APIStatusError, APITimeoutError, RateLimitError

from email_agent.llm.client import ClaudeResponse, ToolUse

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """LLM client for DeepSeek API (OpenAI-compatible).

    Internally converts Anthropic-format messages and tools to OpenAI format,
    and converts OpenAI responses back to the provider-neutral ClaudeResponse/ToolUse types.
    """

    def __init__(self, api_key: str, model: str = "deepseek-chat",
                 base_url: str = "https://api.deepseek.com",
                 max_tokens: int = 1024, temperature: float = 0.0):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def send(self, system_prompt: str, messages: list[dict],
             tools: Optional[list[dict]] = None,
             max_retries: int = 3) -> ClaudeResponse:
        """Send a message to DeepSeek, with retry logic.

        Accepts Anthropic-format messages and tools, converts internally.
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return self._send_inner(system_prompt, messages, tools)
            except (APITimeoutError, RateLimitError) as e:
                last_error = e
                if attempt == max_retries - 1:
                    break
                wait = 2 ** attempt
                logger.warning("DeepSeek API retry %d/%d after %ds: %s",
                               attempt + 1, max_retries, wait, e)
                time.sleep(wait)
            except APIStatusError as e:
                raise RuntimeError(
                    f"DeepSeek API error (status {e.status_code}): {e.message}"
                ) from e

        raise RuntimeError(f"DeepSeek API failed after {max_retries} retries: {last_error}")

    def _send_inner(self, system_prompt: str, messages: list[dict],
                    tools: Optional[list[dict]]) -> ClaudeResponse:
        openai_messages = _build_openai_messages(system_prompt, messages)
        openai_tools = _convert_tools(tools) if tools else None

        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=openai_messages,
        )
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = self.client.chat.completions.create(**kwargs)
        return _parse_openai_response(response)


# ---- Conversion: Anthropic → OpenAI ----

def _build_openai_messages(system_prompt: str, anthropic_messages: list[dict]) -> list[dict]:
    """Convert Anthropic-format messages to OpenAI format."""
    result = []

    if system_prompt:
        result.append({"role": "system", "content": system_prompt})

    for msg in anthropic_messages:
        role = msg["role"]
        content = msg.get("content")

        if isinstance(content, str):
            result.append({"role": role, "content": content})
            continue

        if not isinstance(content, list):
            result.append({"role": role, "content": str(content)})
            continue

        tool_uses = []
        tool_results = []
        text_parts = []

        for block in content:
            block_type = block.get("type", "")
            if block_type == "tool_use":
                tool_uses.append(block)
            elif block_type == "tool_result":
                tool_results.append(block)
            elif block_type == "text":
                text_parts.append(block.get("text", ""))

        # Assistant message with tool_use blocks → OpenAI tool_calls
        if role == "assistant" and tool_uses:
            openai_msg: dict = {"role": "assistant"}
            if text_parts:
                openai_msg["content"] = "\n".join(text_parts)
            else:
                openai_msg["content"] = None
            openai_msg["tool_calls"] = []
            for tu in tool_uses:
                openai_msg["tool_calls"].append({
                    "id": tu["id"],
                    "type": "function",
                    "function": {
                        "name": tu["name"],
                        "arguments": json.dumps(tu["input"], ensure_ascii=False),
                    },
                })
            result.append(openai_msg)

        # User message with tool_result blocks → OpenAI tool messages
        elif role == "user" and tool_results:
            for tr in tool_results:
                result.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_use_id"],
                    "content": tr.get("content", ""),
                })

        # Plain assistant message (no tool calls)
        elif role == "assistant":
            result.append({"role": "assistant", "content": "\n".join(text_parts) or None})

        # Plain user message (no tool results)
        else:
            result.append({"role": role, "content": "\n".join(text_parts) if text_parts else ""})

    return result


def _convert_tools(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic-format tool definitions to OpenAI function format."""
    result = []
    for tool in anthropic_tools:
        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {
                    "type": "object",
                    "properties": {},
                }),
            },
        })
    return result


# ---- Conversion: OpenAI → provider-neutral ----

def _parse_openai_response(response) -> ClaudeResponse:
    """Parse OpenAI chat completion into provider-neutral ClaudeResponse."""
    choice = response.choices[0]
    msg = choice.message

    text = msg.content or ""
    tool_uses = []

    if msg.tool_calls:
        for tc in msg.tool_calls:
            try:
                tool_input = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_input = {}
            tool_uses.append(ToolUse(
                id=tc.id,
                name=tc.function.name,
                input=tool_input,
            ))

    # Map OpenAI finish_reason to Anthropic stop_reason
    finish = choice.finish_reason
    if finish == "tool_calls":
        stop_reason = "tool_use"
    elif finish == "stop":
        stop_reason = "end_turn"
    elif finish == "length":
        stop_reason = "max_tokens"
    else:
        stop_reason = finish or "end_turn"

    return ClaudeResponse(
        text=text,
        stop_reason=stop_reason,
        tool_uses=tool_uses,
    )
