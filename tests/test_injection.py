"""
tests/test_injection.py
CP-5.1: Clipboard is restored to original value after inject (even on exception)
CP-5.2: Empty text does not trigger paste operation
"""
import pytest
from unittest.mock import patch, MagicMock, call
from hypothesis import given, settings
from hypothesis import strategies as st

from clipboard_injector import ClipboardInjector


# ─── CP-5.1: Clipboard restored after inject ──────────────────────────────────

class TestCP51_ClipboardRestored:
    """CP-5.1: Clipboard must be restored to original value after inject, even on exception."""

    def test_clipboard_restored_after_successful_inject(self):
        """After successful inject, clipboard contains original content."""
        original = "original clipboard content"
        injected = "injected text"
        clipboard_state = [original]

        def mock_paste():
            return clipboard_state[0]

        def mock_copy(text):
            clipboard_state[0] = text

        injector = ClipboardInjector()

        with patch("clipboard_injector.pyperclip.paste", side_effect=mock_paste), \
             patch("clipboard_injector.pyperclip.copy", side_effect=mock_copy), \
             patch("clipboard_injector._kb") as mock_kb, \
             patch("clipboard_injector.time.sleep"):
            mock_kb.pressed.return_value.__enter__ = MagicMock(return_value=None)
            mock_kb.pressed.return_value.__exit__ = MagicMock(return_value=False)
            injector.inject_text(injected)

        assert clipboard_state[0] == original

    def test_clipboard_restored_even_on_exception(self):
        """Clipboard must be restored even if an exception occurs during inject."""
        original = "original content"
        clipboard_state = [original]

        def mock_paste():
            return clipboard_state[0]

        def mock_copy(text):
            clipboard_state[0] = text

        injector = ClipboardInjector()

        with patch("clipboard_injector.pyperclip.paste", side_effect=mock_paste), \
             patch("clipboard_injector.pyperclip.copy", side_effect=mock_copy), \
             patch("clipboard_injector._kb") as mock_kb, \
             patch("clipboard_injector.time.sleep"):
            # Make the keyboard press raise an exception
            mock_kb.pressed.side_effect = RuntimeError("keyboard error")
            injector.inject_text("some text")  # should not raise

        # Clipboard must be restored despite the exception
        assert clipboard_state[0] == original

    @given(
        original=st.text(max_size=200),
        injected=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=50)
    def test_property_clipboard_always_restored(self, original, injected):
        """Property: clipboard is always restored to original value after inject."""
        clipboard_state = [original]

        def mock_paste():
            return clipboard_state[0]

        def mock_copy(text):
            clipboard_state[0] = text

        injector = ClipboardInjector()

        with patch("clipboard_injector.pyperclip.paste", side_effect=mock_paste), \
             patch("clipboard_injector.pyperclip.copy", side_effect=mock_copy), \
             patch("clipboard_injector._kb") as mock_kb, \
             patch("clipboard_injector.time.sleep"):
            mock_kb.pressed.return_value.__enter__ = MagicMock(return_value=None)
            mock_kb.pressed.return_value.__exit__ = MagicMock(return_value=False)
            injector.inject_text(injected)

        assert clipboard_state[0] == original


# ─── CP-5.2: Empty text does not trigger paste ────────────────────────────────

class TestCP52_EmptyTextNoPaste:
    """CP-5.2: Empty text must not trigger any paste operation."""

    def test_empty_string_no_paste(self):
        """inject_text('') must not call pyperclip.copy or keyboard."""
        injector = ClipboardInjector()

        with patch("clipboard_injector.pyperclip.copy") as mock_copy, \
             patch("clipboard_injector.pyperclip.paste") as mock_paste, \
             patch("clipboard_injector._kb") as mock_kb:
            injector.inject_text("")

        mock_copy.assert_not_called()
        mock_paste.assert_not_called()
        mock_kb.pressed.assert_not_called()

    def test_none_text_no_paste(self):
        """inject_text(None) must not trigger paste."""
        injector = ClipboardInjector()

        with patch("clipboard_injector.pyperclip.copy") as mock_copy, \
             patch("clipboard_injector._kb") as mock_kb:
            injector.inject_text(None)

        mock_copy.assert_not_called()
        mock_kb.pressed.assert_not_called()

    @given(st.text(max_size=0))
    @settings(max_examples=10)
    def test_property_empty_text_no_paste(self, text):
        """Property: any empty/falsy text must not trigger paste."""
        injector = ClipboardInjector()

        with patch("clipboard_injector.pyperclip.copy") as mock_copy, \
             patch("clipboard_injector._kb") as mock_kb:
            injector.inject_text(text)

        if not text:
            mock_copy.assert_not_called()
