"""
tests/test_notion.py
CP-6.1: Trigger word detected only at start or end of transcript
CP-6.3: enable_notion=False makes no HTTP requests
"""
import pytest
import re
from unittest.mock import patch, MagicMock
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from core.pipeline import _detect_notion_trigger, _remove_trigger_word


# ─── CP-6.1: Trigger word detected only at start or end ───────────────────────

class TestCP61_TriggerWordDetection:
    """CP-6.1: Trigger word must be detected only at the start or end of transcript."""

    TRIGGER = "заметка"

    def test_trigger_at_start_detected(self):
        assert _detect_notion_trigger(f"{self.TRIGGER} купить молоко", self.TRIGGER) is True

    def test_trigger_at_end_detected(self):
        assert _detect_notion_trigger(f"купить молоко {self.TRIGGER}", self.TRIGGER) is True

    def test_trigger_in_middle_not_detected(self):
        """Trigger word in the middle of text must NOT be detected."""
        assert _detect_notion_trigger(f"купить {self.TRIGGER} молоко", self.TRIGGER) is False

    def test_no_trigger_not_detected(self):
        assert _detect_notion_trigger("купить молоко и хлеб", self.TRIGGER) is False

    def test_empty_trigger_not_detected(self):
        assert _detect_notion_trigger("любой текст", "") is False

    def test_trigger_with_punctuation_at_start(self):
        """Trigger with leading punctuation at start is still detected."""
        assert _detect_notion_trigger(f", {self.TRIGGER} текст", self.TRIGGER) is True

    @given(
        prefix=st.text(min_size=1, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя "),
        suffix=st.text(min_size=1, max_size=50, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя "),
    )
    @settings(max_examples=100)
    def test_property_trigger_in_middle_not_detected(self, prefix, suffix):
        """Property: trigger word surrounded by non-empty text on both sides is not detected."""
        assume(prefix.strip() and suffix.strip())
        # Ensure neither prefix nor suffix contains the trigger word
        assume(self.TRIGGER.lower() not in prefix.strip().lower())
        assume(self.TRIGGER.lower() not in suffix.strip().lower())
        text = f"{prefix.strip()} {self.TRIGGER} {suffix.strip()}"
        # Only detect if trigger is at very start or very end
        result = _detect_notion_trigger(text, self.TRIGGER)
        # The trigger is in the middle, so it should NOT be detected
        assert result == False

    @given(
        suffix=st.text(min_size=1, max_size=100, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя "),
    )
    @settings(max_examples=50)
    def test_property_trigger_at_start_always_detected(self, suffix):
        """Property: trigger at the very start is always detected."""
        assume(suffix.strip())
        text = f"{self.TRIGGER} {suffix.strip()}"
        assert _detect_notion_trigger(text, self.TRIGGER) is True

    @given(
        prefix=st.text(min_size=1, max_size=100, alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя "),
    )
    @settings(max_examples=50)
    def test_property_trigger_at_end_always_detected(self, prefix):
        """Property: trigger at the very end is always detected."""
        assume(prefix.strip())
        text = f"{prefix.strip()} {self.TRIGGER}"
        assert _detect_notion_trigger(text, self.TRIGGER) is True


# ─── CP-6.2: Trigger word removed from text ───────────────────────────────────

class TestCP62_TriggerWordRemoval:
    """CP-6.2: After removing trigger word, text must not contain it."""

    TRIGGER = "заметка"

    def test_trigger_removed_from_start(self):
        text = f"{self.TRIGGER} купить молоко"
        result = _remove_trigger_word(text, self.TRIGGER)
        assert self.TRIGGER.lower() not in result.lower()
        assert "купить молоко" in result.lower()

    def test_trigger_removed_from_end(self):
        text = f"купить молоко {self.TRIGGER}"
        result = _remove_trigger_word(text, self.TRIGGER)
        assert self.TRIGGER.lower() not in result.lower()

    @given(
        content=st.text(min_size=5, max_size=100,
                        alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя "),
    )
    @settings(max_examples=50)
    def test_property_trigger_not_in_result_after_removal(self, content):
        """Property: after removal, trigger word is not in the result."""
        assume(content.strip() and "заметка" not in content.lower())
        text = f"заметка {content.strip()}"
        result = _remove_trigger_word(text, "заметка")
        assert "заметка" not in result.lower()


# ─── CP-6.3: enable_notion=False makes no HTTP requests ───────────────────────

class TestCP63_NotionDisabledNoRequests:
    """CP-6.3: When enable_notion=False, no HTTP requests must be made."""

    def test_notion_disabled_no_http_call(self):
        """categorize_and_send_to_notion must not make HTTP requests when notion is disabled."""
        from integrations.notion import categorize_and_send_to_notion

        with patch("integrations.notion.get_enable_notion", return_value=False), \
             patch("integrations.notion.requests.post") as mock_post:
            categorize_and_send_to_notion("some text")

        mock_post.assert_not_called()

    def test_notion_disabled_no_groq_call(self):
        """No LLM call when notion is disabled."""
        from integrations.notion import categorize_and_send_to_notion

        with patch("integrations.notion.get_enable_notion", return_value=False), \
             patch("integrations.notion.Groq") as mock_groq:
            categorize_and_send_to_notion("some text")

        mock_groq.assert_not_called()

    @given(st.text(min_size=0, max_size=500))
    @settings(max_examples=30)
    def test_property_no_requests_when_disabled(self, text):
        """Property: no HTTP requests for any input when notion is disabled."""
        from integrations.notion import categorize_and_send_to_notion

        with patch("integrations.notion.get_enable_notion", return_value=False), \
             patch("integrations.notion.requests.post") as mock_post:
            categorize_and_send_to_notion(text)

        mock_post.assert_not_called()


