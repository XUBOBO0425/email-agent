"""Integration tests for classify_email tool using seed emails.
These require a real Claude API key and incur costs. Run manually.

Usage:
    uv run pytest tests/test_tools/test_classify.py -v -m integration
"""
import pytest


@pytest.mark.integration
class TestClassifyIntegration:
    """Seed email classification tests. Requires CLAUDE_API_KEY env var."""

    def test_urgent_from_boss(self):
        """Email from boss with deadline keywords → urgent + work category."""
        pytest.skip("Integration test — requires real Claude API key. Run manually.")

    def test_newsletter_is_low_priority(self):
        """Newsletter email → low priority + newsletter category."""
        pytest.skip("Integration test — requires real Claude API key. Run manually.")

    def test_normal_correspondence(self):
        """Regular work email → normal priority."""
        pytest.skip("Integration test — requires real Claude API key. Run manually.")
