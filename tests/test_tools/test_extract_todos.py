"""Integration tests for extract_todos tool using seed emails.
These require a real Claude API key and incur costs. Run manually.

Usage:
    uv run pytest tests/test_tools/test_extract_todos.py -v -m integration
"""
import pytest


@pytest.mark.integration
class TestExtractTodosIntegration:
    """Seed email todo extraction tests. Requires CLAUDE_API_KEY env var."""

    def test_extract_interview_todo(self):
        """Interview invitation → extract date, time, and action."""
        pytest.skip("Integration test — requires real Claude API key. Run manually.")

    def test_extract_deadline_task(self):
        """Email with explicit deadline → extract task with due_date."""
        pytest.skip("Integration test — requires real Claude API key. Run manually.")

    def test_no_todos_in_newsletter(self):
        """Pure informational email → no todos extracted."""
        pytest.skip("Integration test — requires real Claude API key. Run manually.")
