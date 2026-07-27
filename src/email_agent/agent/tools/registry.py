from typing import Callable, Any


class ToolRegistry:
    """Registry of tools the agent can use. Each tool has a name,
    an Anthropic-format tool definition, and a handler function."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, definition: dict, handler: Callable):
        self._tools[name] = {
            "definition": definition,
            "handler": handler,
        }

    def get_definitions(self) -> list[dict]:
        """Return tool definitions in Anthropic API format."""
        return [t["definition"] for t in self._tools.values()]

    def execute(self, name: str, input: dict) -> str:
        """Execute a tool by name and return its result as a string."""
        if name not in self._tools:
            return f"Error: unknown tool '{name}'"
        try:
            result = self._tools[name]["handler"](**input)
            return str(result) if not isinstance(result, str) else result
        except Exception as e:
            return f"Error executing {name}: {e}"


# Singleton
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    return _registry
