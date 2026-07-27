import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from anthropic import Anthropic, APIStatusError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict


@dataclass
class ClaudeResponse:
    text: str
    stop_reason: str
    tool_uses: list[ToolUse] = field(default_factory=list)


class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-5",
                 max_tokens: int = 1024, temperature: float = 0.0):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def send(self, system_prompt: str, messages: list[dict],
             tools: Optional[list[dict]] = None,
             max_retries: int = 3) -> ClaudeResponse:
        """Send a message to Claude, with retry logic."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return self._send_inner(system_prompt, messages, tools)
            except (APITimeoutError, RateLimitError) as e:
                last_error = e
                if attempt == max_retries - 1:
                    break
                wait = 2 ** attempt
                logger.warning("Claude API retry %d/%d after %ds: %s",
                               attempt + 1, max_retries, wait, e)
                time.sleep(wait)
            except APIStatusError as e:
                raise RuntimeError(f"Claude API error (status {e.status_code}): {e.message}") from e

        raise RuntimeError(f"Claude API failed after {max_retries} retries: {last_error}")

    def _send_inner(self, system_prompt: str, messages: list[dict],
                    tools: Optional[list[dict]]) -> ClaudeResponse:
        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=messages,
        )
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        tool_uses = []
        text_parts = []
        for block in response.content:
            if block.type == "tool_use":
                tool_uses.append(ToolUse(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))
            elif block.type == "text":
                text_parts.append(block.text)

        return ClaudeResponse(
            text="\n".join(text_parts),
            stop_reason=response.stop_reason,
            tool_uses=tool_uses,
        )
